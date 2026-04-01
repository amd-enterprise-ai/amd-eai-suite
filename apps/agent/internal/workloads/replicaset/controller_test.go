// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package replicaset

import (
	"context"
	"testing"

	"github.com/google/uuid"
	agent "github.com/silogen/agent/internal/common"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
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
)

func setupReconciler(objs ...client.Object) *Reconciler {
	return setupReconcilerWithPublisher(testutils.NewMockPublisher(), objs...)
}

func setupReconcilerWithPublisher(publisher messaging.MessagePublisher, objs ...client.Object) *Reconciler {
	scheme := runtime.NewScheme()
	_ = appsv1.AddToScheme(scheme)

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
			Name:      "nonexistent-replicaset",
			Namespace: "test-namespace",
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, mock.Published)
}

func TestReconcile_AddsFinalizerToNewResource(t *testing.T) {
	replicaSet := &appsv1.ReplicaSet{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-replicaset",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  uuid.New().String(),
				common.ComponentIDLabel: uuid.New().String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
	}

	r := setupReconciler(replicaSet)
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      replicaSet.Name,
			Namespace: replicaSet.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Verify finalizer was added
	var updatedReplicaSet appsv1.ReplicaSet
	err = r.Client.Get(context.Background(), req.NamespacedName, &updatedReplicaSet)
	assert.NoError(t, err)
	assert.True(t, controllerutil.ContainsFinalizer(&updatedReplicaSet, common.WorkloadFinalizer))

	// Verify status message was published
	assert.Len(t, mock.Published, 1)
	statusMsg, ok := mock.Published[0].(*messaging.WorkloadComponentStatusMessage)
	assert.True(t, ok)
	assert.NotEmpty(t, statusMsg.Status)
}

func TestReconcile_DoesNotDuplicateFinalizer(t *testing.T) {
	replicaSet := &appsv1.ReplicaSet{
		ObjectMeta: metav1.ObjectMeta{
			Name:       "test-replicaset",
			Namespace:  "test-namespace",
			Finalizers: []string{common.WorkloadFinalizer},
			Labels: map[string]string{
				common.WorkloadIDLabel:  uuid.New().String(),
				common.ComponentIDLabel: uuid.New().String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
	}

	r := setupReconciler(replicaSet)
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      replicaSet.Name,
			Namespace: replicaSet.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Verify only one finalizer exists
	var updatedReplicaSet appsv1.ReplicaSet
	err = r.Client.Get(context.Background(), req.NamespacedName, &updatedReplicaSet)
	assert.NoError(t, err)
	assert.Len(t, updatedReplicaSet.GetFinalizers(), 1)

	// Verify status message was published
	assert.Len(t, mock.Published, 1)
	statusMsg, ok := mock.Published[0].(*messaging.WorkloadComponentStatusMessage)
	assert.True(t, ok)
	assert.NotEmpty(t, statusMsg.Status)
}

func TestReconcile_HandlesDeletionWithValidLabels(t *testing.T) {
	workloadID := uuid.New()
	componentID := uuid.New()
	now := metav1.Now()

	replicaSet := &appsv1.ReplicaSet{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-replicaset",
			Namespace:         "test-namespace",
			DeletionTimestamp: &now,
			Finalizers:        []string{common.WorkloadFinalizer},
			Labels: map[string]string{
				common.WorkloadIDLabel:  workloadID.String(),
				common.ComponentIDLabel: componentID.String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
		Spec: appsv1.ReplicaSetSpec{
			Selector: &metav1.LabelSelector{
				MatchLabels: map[string]string{"app": "test"},
			},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: map[string]string{"app": "test"},
				},
			},
		},
	}

	r := setupReconciler(replicaSet)
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      replicaSet.Name,
			Namespace: replicaSet.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Verify deletion message was published
	assert.Len(t, mock.Published, 1)
	msg, ok := mock.Published[0].(messaging.WorkloadComponentStatusMessage)
	assert.True(t, ok)
	assert.Equal(t, "test-replicaset", msg.Name)
	assert.Equal(t, "Deleted", msg.Status)
	assert.Equal(t, workloadID.String(), msg.WorkloadID)
	assert.Equal(t, componentID.String(), msg.ID)
}

func TestReconcile_HandlesDeletionWithMissingLabels(t *testing.T) {
	now := metav1.Now()

	replicaSet := &appsv1.ReplicaSet{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-replicaset",
			Namespace:         "test-namespace",
			DeletionTimestamp: &now,
			Finalizers:        []string{common.WorkloadFinalizer},
			// No labels - should still handle deletion gracefully
		},
		Spec: appsv1.ReplicaSetSpec{
			Selector: &metav1.LabelSelector{
				MatchLabels: map[string]string{"app": "test"},
			},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: map[string]string{"app": "test"},
				},
			},
		},
	}

	r := setupReconciler(replicaSet)
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      replicaSet.Name,
			Namespace: replicaSet.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Verify no message was published (extraction failed)
	assert.Empty(t, mock.Published)
}

func TestReconcile_PublishesAutoDiscoveryMessage(t *testing.T) {
	workloadID := uuid.New()
	componentID := uuid.New()
	projectID := uuid.New()

	replicaSet := &appsv1.ReplicaSet{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-replicaset",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  workloadID.String(),
				common.ComponentIDLabel: componentID.String(),
				agent.ProjectIDLabel:    projectID.String(),
			},
			Annotations: map[string]string{
				agent.AutoDiscoveredAnnotation: "true",
				agent.SubmitterAnnotation:      "user@example.com",
			},
		},
	}

	r := setupReconciler(replicaSet)
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      replicaSet.Name,
			Namespace: replicaSet.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Should publish both auto-discovery and status messages
	assert.Len(t, mock.Published, 2)

	autoDiscoveryMsg, ok := mock.Published[0].(*messaging.AutoDiscoveredWorkloadComponentMessage)
	assert.True(t, ok)
	assert.Equal(t, "test-replicaset", autoDiscoveryMsg.Name)
	assert.Equal(t, workloadID.String(), autoDiscoveryMsg.WorkloadID)
	assert.Equal(t, componentID.String(), autoDiscoveryMsg.ComponentID)
	assert.Equal(t, projectID.String(), autoDiscoveryMsg.ProjectID)

	statusMsg, ok := mock.Published[1].(*messaging.WorkloadComponentStatusMessage)
	assert.True(t, ok)
	assert.NotEmpty(t, statusMsg.Status)
}

func TestReconcile_SkipsResourceWithoutLabels(t *testing.T) {
	replicaSet := &appsv1.ReplicaSet{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-replicaset",
			Namespace: "test-namespace",
			// No labels
		},
	}

	r := setupReconciler(replicaSet)
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      replicaSet.Name,
			Namespace: replicaSet.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Should not publish any messages
	assert.Empty(t, mock.Published)
}

func TestReconcile_PublishesStatusMessage(t *testing.T) {
	workloadID := uuid.New()
	componentID := uuid.New()

	replicaSet := &appsv1.ReplicaSet{
		TypeMeta: metav1.TypeMeta{
			APIVersion: "apps/v1",
			Kind:       "ReplicaSet",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-replicaset",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  workloadID.String(),
				common.ComponentIDLabel: componentID.String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
		Status: appsv1.ReplicaSetStatus{
			Replicas:      3,
			ReadyReplicas: 3,
		},
	}

	r := setupReconciler(replicaSet)
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      replicaSet.Name,
			Namespace: replicaSet.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Should publish status message
	require.Len(t, mock.Published, 1)
	statusMsg, ok := mock.Published[0].(*messaging.WorkloadComponentStatusMessage)
	require.True(t, ok)
	assert.Equal(t, "test-replicaset", statusMsg.Name)
	// Note: Kind field is empty in tests due to fake client limitation with GVK preservation
	// This works correctly in real implementations where Get() preserves TypeMeta
	assert.Equal(t, common.StatusRunning, statusMsg.Status)
	assert.NotNil(t, statusMsg.StatusReason)
	assert.Equal(t, workloadID.String(), statusMsg.WorkloadID)
	assert.Equal(t, componentID.String(), statusMsg.ID)
}
