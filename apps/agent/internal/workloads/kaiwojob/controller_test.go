// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package kaiwojob

import (
	"context"
	"errors"
	"testing"

	"github.com/google/uuid"
	agent "github.com/silogen/agent/internal/common"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	"sigs.k8s.io/controller-runtime/pkg/reconcile"

	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/testutils"
	"github.com/silogen/agent/internal/workloads/common"
	kaiwov1alpha1 "github.com/silogen/kaiwo/apis/kaiwo/v1alpha1"
)

func setupReconciler(objs ...client.Object) *Reconciler {
	return setupReconcilerWithPublisher(testutils.NewMockPublisher(), objs...)
}

func setupReconcilerWithPublisher(publisher messaging.MessagePublisher, objs ...client.Object) *Reconciler {
	scheme := runtime.NewScheme()
	_ = kaiwov1alpha1.AddToScheme(scheme)

	fakeClient := fake.NewClientBuilder().
		WithScheme(scheme).
		WithObjects(objs...).
		Build()

	return &Reconciler{Client: fakeClient, Publisher: publisher}
}

func TestReconcile_ResourceNotFound(t *testing.T) {
	r := setupReconciler()
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      "nonexistent-kaiwojob",
			Namespace: "test-namespace",
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, mock.Published)
}

func TestReconcile_AddsFinalizerToNewResource(t *testing.T) {
	kj := &kaiwov1alpha1.KaiwoJob{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-kaiwojob",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  uuid.New().String(),
				common.ComponentIDLabel: uuid.New().String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
		Status: kaiwov1alpha1.KaiwoJobStatus{
			CommonStatusSpec: kaiwov1alpha1.CommonStatusSpec{
				Status: kaiwov1alpha1.WorkloadStatusRunning,
			},
		},
	}

	r := setupReconciler(kj)
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{Name: kj.Name, Namespace: kj.Namespace},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	var updated kaiwov1alpha1.KaiwoJob
	err = r.Client.Get(context.Background(), req.NamespacedName, &updated)
	assert.NoError(t, err)
	assert.True(t, controllerutil.ContainsFinalizer(&updated, common.WorkloadFinalizer))

	// Verify status message was published
	assert.Len(t, mock.Published, 1)
	statusMsg, ok := mock.Published[0].(*messaging.WorkloadComponentStatusMessage)
	assert.True(t, ok)
	assert.NotEmpty(t, statusMsg.Status)
}

func TestReconcile_DoesNotDuplicateFinalizer(t *testing.T) {
	kj := &kaiwov1alpha1.KaiwoJob{
		ObjectMeta: metav1.ObjectMeta{
			Name:       "test-kaiwojob",
			Namespace:  "test-namespace",
			Finalizers: []string{common.WorkloadFinalizer},
			Labels: map[string]string{
				common.WorkloadIDLabel:  uuid.New().String(),
				common.ComponentIDLabel: uuid.New().String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
		Status: kaiwov1alpha1.KaiwoJobStatus{
			CommonStatusSpec: kaiwov1alpha1.CommonStatusSpec{
				Status: kaiwov1alpha1.WorkloadStatusRunning,
			},
		},
	}

	r := setupReconciler(kj)
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{Name: kj.Name, Namespace: kj.Namespace},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	var updated kaiwov1alpha1.KaiwoJob
	err = r.Client.Get(context.Background(), req.NamespacedName, &updated)
	assert.NoError(t, err)
	assert.Len(t, updated.GetFinalizers(), 1)

	// Verify status message was published
	assert.Len(t, mock.Published, 1)
	statusMsg, ok := mock.Published[0].(*messaging.WorkloadComponentStatusMessage)
	assert.True(t, ok)
	assert.NotEmpty(t, statusMsg.Status)
}

func TestReconcile_HandlesDeletionWithValidLabels(t *testing.T) {
	workloadID := uuid.New()
	componentID := uuid.New()
	projectID := uuid.New()
	now := metav1.Now()

	kj := &kaiwov1alpha1.KaiwoJob{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-kaiwojob",
			Namespace:         "test-namespace",
			DeletionTimestamp: &now,
			Finalizers:        []string{common.WorkloadFinalizer},
			Labels: map[string]string{
				common.WorkloadIDLabel:  workloadID.String(),
				common.ComponentIDLabel: componentID.String(),
				agent.ProjectIDLabel:    projectID.String(),
			},
		},
	}

	r := setupReconciler(kj)
	mock := r.Publisher.(*testutils.MockPublisher)

	result, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: kj.Name, Namespace: kj.Namespace},
	})

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Len(t, mock.Published, 1)

	msg, ok := mock.Published[0].(messaging.WorkloadComponentStatusMessage)
	assert.True(t, ok)
	assert.Equal(t, "test-kaiwojob", msg.Name)
	assert.Equal(t, "Deleted", msg.Status)
	assert.Equal(t, workloadID.String(), msg.WorkloadID)
	assert.Equal(t, componentID.String(), msg.ID)
}

func TestReconcile_HandlesDeletionWithMissingLabels(t *testing.T) {
	now := metav1.Now()

	kj := &kaiwov1alpha1.KaiwoJob{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-kaiwojob",
			Namespace:         "test-namespace",
			DeletionTimestamp: &now,
			Finalizers:        []string{common.WorkloadFinalizer},
			// No labels - should still handle deletion gracefully
		},
	}

	r := setupReconciler(kj)
	mock := r.Publisher.(*testutils.MockPublisher)

	result, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: kj.Name, Namespace: kj.Namespace},
	})

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, mock.Published)
}

func TestReconcile_DeletionPublishFailure_ReturnsError(t *testing.T) {
	now := metav1.Now()

	kj := &kaiwov1alpha1.KaiwoJob{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-kaiwojob",
			Namespace:         "test-namespace",
			DeletionTimestamp: &now,
			Finalizers:        []string{common.WorkloadFinalizer},
			Labels: map[string]string{
				common.WorkloadIDLabel:  uuid.New().String(),
				common.ComponentIDLabel: uuid.New().String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
	}

	pubErr := errors.New("publish failed")
	r := setupReconcilerWithPublisher(testutils.NewMockFailingPublisher(pubErr), kj)

	_, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: kj.Name, Namespace: kj.Namespace},
	})

	assert.Error(t, err)
	assert.ErrorIs(t, err, pubErr)
}

func TestReconcile_PublishesAutoDiscoveryMessage(t *testing.T) {
	submitter := "system:serviceaccount:ns:my-sa"
	kj := &kaiwov1alpha1.KaiwoJob{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-kaiwojob",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  uuid.New().String(),
				common.ComponentIDLabel: uuid.New().String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
			Annotations: map[string]string{
				agent.AutoDiscoveredAnnotation: agent.AutoDiscoveredValue,
				agent.SubmitterAnnotation:      submitter,
			},
		},
		Status: kaiwov1alpha1.KaiwoJobStatus{
			CommonStatusSpec: kaiwov1alpha1.CommonStatusSpec{
				Status: kaiwov1alpha1.WorkloadStatusRunning,
			},
		},
	}

	r := setupReconciler(kj)
	mock := r.Publisher.(*testutils.MockPublisher)

	result, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: kj.Name, Namespace: kj.Namespace},
	})

	require.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	require.Len(t, mock.Published, 2)

	autoMsg, ok := mock.Published[0].(*messaging.AutoDiscoveredWorkloadComponentMessage)
	require.True(t, ok)
	assert.Equal(t, kj.Name, autoMsg.Name)
	assert.NotNil(t, autoMsg.Submitter)
	assert.Contains(t, *autoMsg.Submitter, "ns:my-sa")

	statusMsg, ok := mock.Published[1].(*messaging.WorkloadComponentStatusMessage)
	require.True(t, ok)
	assert.NotEmpty(t, statusMsg.Status)
}

func TestReconcile_AutoDiscoveryPublishFailure_ReturnsError(t *testing.T) {
	kj := &kaiwov1alpha1.KaiwoJob{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-kaiwojob",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  uuid.New().String(),
				common.ComponentIDLabel: uuid.New().String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
			Annotations: map[string]string{
				agent.AutoDiscoveredAnnotation: agent.AutoDiscoveredValue,
			},
		},
		Status: kaiwov1alpha1.KaiwoJobStatus{
			CommonStatusSpec: kaiwov1alpha1.CommonStatusSpec{
				Status: kaiwov1alpha1.WorkloadStatusRunning,
			},
		},
	}

	pubErr := errors.New("auto-discovery publish failed")
	publisher := testutils.NewMockSelectiveFailingPublisher(func(message interface{}) bool {
		_, ok := message.(*messaging.AutoDiscoveredWorkloadComponentMessage)
		return ok
	}, pubErr)
	r := setupReconcilerWithPublisher(publisher, kj)

	_, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: kj.Name, Namespace: kj.Namespace},
	})
	assert.Error(t, err)
	assert.ErrorIs(t, err, pubErr)
	assert.Empty(t, publisher.Published)
}

func TestReconcile_StatusPublishFailure_ReturnsError(t *testing.T) {
	kj := &kaiwov1alpha1.KaiwoJob{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-kaiwojob",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  uuid.New().String(),
				common.ComponentIDLabel: uuid.New().String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
		Status: kaiwov1alpha1.KaiwoJobStatus{
			CommonStatusSpec: kaiwov1alpha1.CommonStatusSpec{
				Status: kaiwov1alpha1.WorkloadStatusRunning,
			},
		},
	}

	pubErr := errors.New("status publish failed")
	publisher := testutils.NewMockSelectiveFailingPublisher(func(message interface{}) bool {
		_, ok := message.(*messaging.WorkloadComponentStatusMessage)
		return ok
	}, pubErr)
	r := setupReconcilerWithPublisher(publisher, kj)

	_, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: kj.Name, Namespace: kj.Namespace},
	})
	assert.Error(t, err)
	assert.ErrorIs(t, err, pubErr)
}
