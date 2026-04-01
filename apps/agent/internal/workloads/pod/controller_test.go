// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package pod

import (
	"context"
	"testing"

	"github.com/google/uuid"
	agent "github.com/silogen/agent/internal/common"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"
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
	_ = corev1.AddToScheme(scheme)

	fakeClient := fake.NewClientBuilder().WithScheme(scheme).WithObjects(objs...).Build()
	return &Reconciler{Client: fakeClient, Publisher: publisher}
}

func TestReconcile_PodNotFound(t *testing.T) {
	r := setupReconciler()
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      "nonexistent-pod",
			Namespace: "test-namespace",
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, mock.Published)
}

func TestReconcile_PodWithWorkloadLabel_AddsFinalizer(t *testing.T) {
	pod := &corev1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-pod",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  uuid.New().String(),
				common.ComponentIDLabel: uuid.New().String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
		Spec: corev1.PodSpec{
			Containers: []corev1.Container{
				{Name: "test", Image: "test:latest"},
			},
		},
		Status: corev1.PodStatus{
			Phase: corev1.PodRunning,
		},
	}

	r := setupReconciler(pod)
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      pod.Name,
			Namespace: pod.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Verify finalizer was added (pod has workload-id label)
	var updatedPod corev1.Pod
	err = r.Client.Get(context.Background(), req.NamespacedName, &updatedPod)
	assert.NoError(t, err)
	assert.Contains(t, updatedPod.GetFinalizers(), common.WorkloadFinalizer)

	// Verify status message was published
	assert.Len(t, mock.Published, 1)
	statusMsg, ok := mock.Published[0].(*messaging.WorkloadComponentStatusMessage)
	assert.True(t, ok)
	assert.NotEmpty(t, statusMsg.Status)
}

func TestReconcile_PodWithoutWorkloadLabel_NoFinalizer(t *testing.T) {
	pod := &corev1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-pod",
			Namespace: "test-namespace",
			// No workload-id label
		},
		Spec: corev1.PodSpec{
			Containers: []corev1.Container{
				{Name: "test", Image: "test:latest"},
			},
		},
	}

	r := setupReconciler(pod)
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      pod.Name,
			Namespace: pod.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Verify no finalizer was added (pod has no workload-id label)
	var updatedPod corev1.Pod
	err = r.Client.Get(context.Background(), req.NamespacedName, &updatedPod)
	assert.NoError(t, err)
	assert.Empty(t, updatedPod.GetFinalizers())
	assert.Empty(t, mock.Published)
}

func TestReconcile_PodBeingDeleted_WithValidLabels(t *testing.T) {
	workloadID := uuid.New()
	componentID := uuid.New()
	projectID := uuid.New()
	now := metav1.Now()

	pod := &corev1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-pod",
			Namespace:         "test-namespace",
			DeletionTimestamp: &now,
			Finalizers:        []string{common.WorkloadFinalizer}, // Our finalizer
			Labels: map[string]string{
				common.WorkloadIDLabel:  workloadID.String(),
				common.ComponentIDLabel: componentID.String(),
				agent.ProjectIDLabel:    projectID.String(),
			},
		},
		Spec: corev1.PodSpec{
			Containers: []corev1.Container{
				{Name: "test", Image: "test:latest"},
			},
		},
	}

	r := setupReconciler(pod)
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      pod.Name,
			Namespace: pod.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Verify deletion message was published
	assert.Len(t, mock.Published, 1)
	msg, ok := mock.Published[0].(messaging.WorkloadComponentStatusMessage)
	assert.True(t, ok)
	assert.Equal(t, "test-pod", msg.Name)
	assert.Equal(t, "Deleted", msg.Status)
	assert.Equal(t, workloadID.String(), msg.WorkloadID)
	assert.Equal(t, componentID.String(), msg.ID)
}

func TestReconcile_PodBeingDeleted_MissingLabels(t *testing.T) {
	now := metav1.Now()

	pod := &corev1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-pod",
			Namespace:         "test-namespace",
			DeletionTimestamp: &now,
			Finalizers:        []string{"some-other-finalizer"},
			// No workload labels
		},
		Spec: corev1.PodSpec{
			Containers: []corev1.Container{
				{Name: "test", Image: "test:latest"},
			},
		},
	}

	r := setupReconciler(pod)
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      pod.Name,
			Namespace: pod.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Should not publish when extraction fails
	assert.Empty(t, mock.Published)
}

func TestReconcile_PodBeingDeleted_PublishError(t *testing.T) {
	workloadID := uuid.New()
	componentID := uuid.New()
	projectID := uuid.New()
	now := metav1.Now()

	pod := &corev1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-pod",
			Namespace:         "test-namespace",
			DeletionTimestamp: &now,
			Finalizers:        []string{common.WorkloadFinalizer}, // Our finalizer
			Labels: map[string]string{
				common.WorkloadIDLabel:  workloadID.String(),
				common.ComponentIDLabel: componentID.String(),
				agent.ProjectIDLabel:    projectID.String(),
			},
		},
		Spec: corev1.PodSpec{
			Containers: []corev1.Container{
				{Name: "test", Image: "test:latest"},
			},
		},
	}

	mock := testutils.NewMockFailingPublisher(assert.AnError)
	r := setupReconcilerWithPublisher(mock, pod)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      pod.Name,
			Namespace: pod.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	// Should return error (triggers requeue) when publish fails
	assert.Error(t, err)
	assert.ErrorIs(t, err, assert.AnError)
	assert.Equal(t, ctrl.Result{}, result)

	// Verify publish failed and no message was added to Published list
	assert.Empty(t, mock.Published)

	// Verify finalizer is still present (deletion blocked until publish succeeds)
	var fetchedPod corev1.Pod
	err = r.Client.Get(context.Background(), types.NamespacedName{Name: pod.Name, Namespace: pod.Namespace}, &fetchedPod)
	assert.NoError(t, err)
	assert.True(t, controllerutil.ContainsFinalizer(&fetchedPod, common.WorkloadFinalizer))
}

func TestReconcile_Pod_AutoDiscoveryBehavior(t *testing.T) {
	tests := []struct {
		name                   string
		autoDiscovered         bool
		submitter              string
		expectedMsgCount       int
		expectedSubmitter      *string
		expectAutoDiscoveryMsg bool
	}{
		{
			name:                   "auto-discovered with submitter",
			autoDiscovered:         true,
			submitter:              "oidc:user@example.com",
			expectedMsgCount:       2,
			expectedSubmitter:      strPtr("user@example.com"),
			expectAutoDiscoveryMsg: true,
		},
		{
			name:                   "auto-discovered without submitter",
			autoDiscovered:         true,
			submitter:              "",
			expectedMsgCount:       2,
			expectedSubmitter:      nil,
			expectAutoDiscoveryMsg: true,
		},
		{
			name:                   "not auto-discovered",
			autoDiscovered:         false,
			submitter:              "",
			expectedMsgCount:       1,
			expectedSubmitter:      nil,
			expectAutoDiscoveryMsg: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			annotations := map[string]string{}
			if tt.autoDiscovered {
				annotations[agent.AutoDiscoveredAnnotation] = "true"
			}
			if tt.submitter != "" {
				annotations[agent.SubmitterAnnotation] = tt.submitter
			}

			pod := &corev1.Pod{
				ObjectMeta: metav1.ObjectMeta{
					Name:      "test-pod",
					Namespace: "test-namespace",
					Labels: map[string]string{
						common.WorkloadIDLabel:  uuid.New().String(),
						common.ComponentIDLabel: uuid.New().String(),
						agent.ProjectIDLabel:    uuid.New().String(),
					},
					Annotations: annotations,
				},
				Status: corev1.PodStatus{
					Phase: corev1.PodRunning,
				},
			}

			reconciler := setupReconciler(pod)
			ctx := ctrl.LoggerInto(context.Background(), zap.New())

			result, err := reconciler.Reconcile(ctx, ctrl.Request{
				NamespacedName: types.NamespacedName{
					Name:      pod.Name,
					Namespace: pod.Namespace,
				},
			})

			require.NoError(t, err)
			assert.Equal(t, ctrl.Result{}, result)

			mockPub := reconciler.Publisher.(*testutils.MockPublisher)
			require.Len(t, mockPub.Published, tt.expectedMsgCount)

			if tt.expectAutoDiscoveryMsg {
				autoDiscMsg, ok := mockPub.Published[0].(*messaging.AutoDiscoveredWorkloadComponentMessage)
				require.True(t, ok)
				if tt.expectedSubmitter != nil {
					assert.NotNil(t, autoDiscMsg.Submitter)
					assert.Equal(t, *tt.expectedSubmitter, *autoDiscMsg.Submitter)
				} else {
					assert.Nil(t, autoDiscMsg.Submitter)
				}

				statusMsg, ok := mockPub.Published[1].(*messaging.WorkloadComponentStatusMessage)
				require.True(t, ok)
				assert.Equal(t, "Running", statusMsg.Status)
			} else {
				statusMsg, ok := mockPub.Published[0].(*messaging.WorkloadComponentStatusMessage)
				require.True(t, ok)
				assert.Equal(t, "Running", statusMsg.Status)
			}
		})
	}
}

func strPtr(s string) *string {
	return &s
}

func TestReconcile_Pod_StatusPublishFailure(t *testing.T) {
	pod := &corev1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-pod",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  "827862af-41b9-4bd6-bd8d-04e4e866dff3",
				common.ComponentIDLabel: "98a47b94-3753-48b7-9b95-0b91f2df27b0",
				agent.ProjectIDLabel:    "121aede7-b363-4188-8d5a-2e034e4d0b3f",
			},
		},
		Status: corev1.PodStatus{
			Phase: corev1.PodRunning,
		},
	}

	mock := testutils.NewMockFailingPublisher(assert.AnError)
	r := setupReconcilerWithPublisher(mock, pod)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      pod.Name,
			Namespace: pod.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	// Should return error (triggers automatic requeue) when status publish fails
	assert.Error(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, mock.Published)
}
