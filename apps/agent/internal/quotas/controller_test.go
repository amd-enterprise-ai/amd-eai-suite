// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package quotas

import (
	"context"
	"testing"
	"time"

	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/testutils"
	kaiwov1alpha1 "github.com/silogen/kaiwo/apis/kaiwo/v1alpha1"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	clientgoscheme "k8s.io/client-go/kubernetes/scheme"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
	kueuev1beta1 "sigs.k8s.io/kueue/apis/kueue/v1beta1"
)

func setupQueueConfigReconciler(queueConfig runtime.Object) (*KaiwoQueueConfigReconciler, messaging.MessagePublisher) {
	return setupQueueConfigReconcilerWithPublisher(testutils.NewMockPublisher(), queueConfig)
}

func setupQueueConfigReconcilerWithPublisher(publisher messaging.MessagePublisher, queueConfig runtime.Object) (*KaiwoQueueConfigReconciler, messaging.MessagePublisher) {
	s := runtime.NewScheme()
	_ = clientgoscheme.AddToScheme(s)
	_ = kaiwov1alpha1.AddToScheme(s)
	_ = kueuev1beta1.AddToScheme(s)

	fakeClientBuilder := fake.NewClientBuilder().WithScheme(s)
	if queueConfig != nil {
		fakeClientBuilder.WithRuntimeObjects(queueConfig)
	}
	fakeClient := fakeClientBuilder.Build()

	// Use provided publisher or create default mock
	if publisher == nil {
		publisher = testutils.NewMockPublisher()
	}

	reconciler := &KaiwoQueueConfigReconciler{
		Client:    fakeClient,
		Publisher: publisher,
	}

	return reconciler, publisher
}

func TestReconcile_AddsFinalizer(t *testing.T) {
	config := &kaiwov1alpha1.KaiwoQueueConfig{
		ObjectMeta: metav1.ObjectMeta{
			Name: "test-config",
		},
		Spec: kaiwov1alpha1.KaiwoQueueConfigSpec{
			ClusterQueues: []kaiwov1alpha1.ClusterQueue{},
		},
	}

	reconciler, publisher := setupQueueConfigReconciler(config)
	mockPub := publisher.(*testutils.MockPublisher)
	ctx := context.Background()

	_, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{Name: "test-config"},
	})

	require.NoError(t, err)

	// Verify finalizer was added
	var updated kaiwov1alpha1.KaiwoQueueConfig
	err = reconciler.Get(ctx, types.NamespacedName{Name: "test-config"}, &updated)
	require.NoError(t, err)
	assert.Contains(t, updated.Finalizers, kaiwoQueueConfigFinalizer)

	// Should publish status
	require.Len(t, mockPub.Published, 1)
	statusMsg, ok := mockPub.Published[0].(*messaging.ClusterQuotasStatusMessage)
	require.True(t, ok)
	assert.Equal(t, messaging.MessageTypeClusterQuotasStatusMessage, statusMsg.MessageType)
}

func TestReconcile_PublishesStatusUpdate(t *testing.T) {
	config := &kaiwov1alpha1.KaiwoQueueConfig{
		ObjectMeta: metav1.ObjectMeta{
			Name:       "test-config",
			Finalizers: []string{kaiwoQueueConfigFinalizer},
		},
		Spec: kaiwov1alpha1.KaiwoQueueConfigSpec{
			ClusterQueues: []kaiwov1alpha1.ClusterQueue{
				{
					Name:       "queue1",
					Namespaces: []string{"ns1", "ns2"},
					Spec: kaiwov1alpha1.ClusterQueueSpec{
						ResourceGroups: []kueuev1beta1.ResourceGroup{
							{
								Flavors: []kueuev1beta1.FlavorQuotas{
									{
										Resources: []kueuev1beta1.ResourceQuota{
											{Name: CPUResource, NominalQuota: resource.MustParse("4000m")},
											{Name: MemoryResource, NominalQuota: resource.MustParse("8Gi")},
											{Name: AMDGPUResource, NominalQuota: resource.MustParse("2")},
										},
									},
								},
							},
						},
					},
				},
				{
					Name:       "queue2",
					Namespaces: nil,
					Spec: kaiwov1alpha1.ClusterQueueSpec{
						ResourceGroups: []kueuev1beta1.ResourceGroup{
							{
								Flavors: []kueuev1beta1.FlavorQuotas{
									{
										Resources: []kueuev1beta1.ResourceQuota{
											{Name: CPUResource, NominalQuota: resource.MustParse("4000m")},
											{Name: MemoryResource, NominalQuota: resource.MustParse("8Gi")},
											{Name: NVIDIAGPUResource, NominalQuota: resource.MustParse("1")},
										},
									},
								},
							},
						},
					},
				},
			},
		},
		Status: kaiwov1alpha1.KaiwoQueueConfigStatus{
			Status: kaiwov1alpha1.QueueConfigStatusReady,
		},
	}

	reconciler, publisher := setupQueueConfigReconciler(config)
	mockPub := publisher.(*testutils.MockPublisher)
	ctx := context.Background()

	_, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{Name: "test-config"},
	})

	require.NoError(t, err)

	// Should publish status with quota allocations
	require.Len(t, mockPub.Published, 1)
	statusMsg, ok := mockPub.Published[0].(*messaging.ClusterQuotasStatusMessage)
	require.True(t, ok)
	assert.Equal(t, messaging.MessageTypeClusterQuotasStatusMessage, statusMsg.MessageType)
	assert.Len(t, statusMsg.QuotaAllocations, 2)

	allocation := statusMsg.QuotaAllocations[0]
	assert.Equal(t, "queue1", allocation.QuotaName)
	assert.Equal(t, []string{"ns1", "ns2"}, allocation.Namespaces)
	assert.Equal(t, int64(4000), allocation.CPUMilliCores)
	assert.Equal(t, int64(2), allocation.GPUCount)

	allocationNoNamespace := statusMsg.QuotaAllocations[1]
	assert.Equal(t, "queue2", allocationNoNamespace.QuotaName)
	assert.Equal(t, []string{}, allocationNoNamespace.Namespaces)
	assert.Equal(t, int64(1), allocationNoNamespace.GPUCount)
}

func TestReconcile_DeletionPublishesEmptyQuotas(t *testing.T) {
	now := metav1.Now()
	config := &kaiwov1alpha1.KaiwoQueueConfig{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-config",
			Finalizers:        []string{kaiwoQueueConfigFinalizer},
			DeletionTimestamp: &now,
		},
		Spec: kaiwov1alpha1.KaiwoQueueConfigSpec{
			ClusterQueues: []kaiwov1alpha1.ClusterQueue{
				{
					Name:       "queue1",
					Namespaces: []string{"ns1"},
				},
			},
		},
	}

	reconciler, publisher := setupQueueConfigReconciler(config)
	mockPub := publisher.(*testutils.MockPublisher)
	ctx := context.Background()

	_, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{Name: "test-config"},
	})

	require.NoError(t, err)

	// Should publish empty quota allocations
	require.Len(t, mockPub.Published, 1)
	statusMsg, ok := mockPub.Published[0].(*messaging.ClusterQuotasStatusMessage)
	require.True(t, ok)
	assert.Equal(t, messaging.MessageTypeClusterQuotasStatusMessage, statusMsg.MessageType)
	assert.Empty(t, statusMsg.QuotaAllocations)
	assert.NotNil(t, statusMsg.QuotaAllocations)
	assert.WithinDuration(t, time.Now(), statusMsg.UpdatedAt, 2*time.Second)
}

func TestReconcile_NotFound(t *testing.T) {
	reconciler, publisher := setupQueueConfigReconciler(nil)
	mockPub := publisher.(*testutils.MockPublisher)
	ctx := context.Background()

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{Name: "non-existent"},
	})

	require.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, mockPub.Published)
}

func TestReconcile_FailedStatusPublishesFailureMessage(t *testing.T) {
	config := &kaiwov1alpha1.KaiwoQueueConfig{
		ObjectMeta: metav1.ObjectMeta{
			Name:       "test-config",
			Finalizers: []string{kaiwoQueueConfigFinalizer},
		},
		Spec: kaiwov1alpha1.KaiwoQueueConfigSpec{
			ClusterQueues: []kaiwov1alpha1.ClusterQueue{
				{
					Name:       "queue1",
					Namespaces: []string{"ns1"},
				},
			},
		},
		Status: kaiwov1alpha1.KaiwoQueueConfigStatus{
			Status: kaiwov1alpha1.QueueConfigStatusFailed,
		},
	}

	reconciler, publisher := setupQueueConfigReconciler(config)
	mockPub := publisher.(*testutils.MockPublisher)
	ctx := context.Background()

	_, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{Name: "test-config"},
	})

	require.NoError(t, err)

	// Should publish failure message
	require.Len(t, mockPub.Published, 1)
	failureMsg, ok := mockPub.Published[0].(*messaging.ClusterQuotaFailureMessage)
	require.True(t, ok)
	assert.Equal(t, messaging.MessageTypeClusterQuotasFailureMessage, failureMsg.MessageType)
	assert.WithinDuration(t, time.Now(), failureMsg.UpdatedAt, 2*time.Second)
}

func TestReconcile_PublishFailureRequeues(t *testing.T) {
	config := &kaiwov1alpha1.KaiwoQueueConfig{
		ObjectMeta: metav1.ObjectMeta{
			Name:       "test-config",
			Finalizers: []string{kaiwoQueueConfigFinalizer},
		},
		Spec: kaiwov1alpha1.KaiwoQueueConfigSpec{
			ClusterQueues: []kaiwov1alpha1.ClusterQueue{
				{
					Name:       "queue1",
					Namespaces: []string{"ns1"},
				},
			},
		},
	}

	// Use setup with failing publisher
	failingPub := testutils.NewMockFailingPublisher(assert.AnError)
	reconciler, _ := setupQueueConfigReconcilerWithPublisher(failingPub, config)

	result, err := reconciler.Reconcile(context.Background(), ctrl.Request{
		NamespacedName: types.NamespacedName{Name: "test-config"},
	})

	// Should return error and request requeue
	require.Error(t, err)
	assert.Equal(t, ctrl.Result{}, result)
}

func TestReconcile_DeletionPublishFailureRequeues(t *testing.T) {
	now := metav1.Now()
	config := &kaiwov1alpha1.KaiwoQueueConfig{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-config",
			Finalizers:        []string{kaiwoQueueConfigFinalizer},
			DeletionTimestamp: &now,
		},
		Spec: kaiwov1alpha1.KaiwoQueueConfigSpec{
			ClusterQueues: []kaiwov1alpha1.ClusterQueue{},
		},
	}

	// Use setup with failing publisher
	failingPub := testutils.NewMockFailingPublisher(assert.AnError)
	reconciler, _ := setupQueueConfigReconcilerWithPublisher(failingPub, config)

	result, err := reconciler.Reconcile(context.Background(), ctrl.Request{
		NamespacedName: types.NamespacedName{Name: "test-config"},
	})

	// Should return error and request requeue
	require.Error(t, err)
	assert.Equal(t, ctrl.Result{}, result)
}
