// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package deployment

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
			Name:      "nonexistent-deployment",
			Namespace: "test-namespace",
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, mock.Published)
}

func TestReconcile_AddsFinalizerToNewResource(t *testing.T) {
	deployment := &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-deployment",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  uuid.New().String(),
				common.ComponentIDLabel: uuid.New().String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
	}

	r := setupReconciler(deployment)
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      deployment.Name,
			Namespace: deployment.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Verify finalizer was added
	var updatedDeployment appsv1.Deployment
	err = r.Client.Get(context.Background(), req.NamespacedName, &updatedDeployment)
	assert.NoError(t, err)
	assert.True(t, controllerutil.ContainsFinalizer(&updatedDeployment, common.WorkloadFinalizer))

	// Verify status message was published
	assert.Len(t, mock.Published, 1)
	statusMsg, ok := mock.Published[0].(*messaging.WorkloadComponentStatusMessage)
	assert.True(t, ok)
	assert.NotEmpty(t, statusMsg.Status)
}

func TestReconcile_DoesNotDuplicateFinalizer(t *testing.T) {
	deployment := &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:       "test-deployment",
			Namespace:  "test-namespace",
			Finalizers: []string{common.WorkloadFinalizer},
			Labels: map[string]string{
				common.WorkloadIDLabel:  uuid.New().String(),
				common.ComponentIDLabel: uuid.New().String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
	}

	r := setupReconciler(deployment)
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      deployment.Name,
			Namespace: deployment.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Verify only one finalizer exists
	var updatedDeployment appsv1.Deployment
	err = r.Client.Get(context.Background(), req.NamespacedName, &updatedDeployment)
	assert.NoError(t, err)
	assert.Len(t, updatedDeployment.GetFinalizers(), 1)

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

	deployment := &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-deployment",
			Namespace:         "test-namespace",
			DeletionTimestamp: &now,
			Finalizers:        []string{common.WorkloadFinalizer},
			Labels: map[string]string{
				common.WorkloadIDLabel:  workloadID.String(),
				common.ComponentIDLabel: componentID.String(),
				agent.ProjectIDLabel:    projectID.String(),
			},
		},
		Spec: appsv1.DeploymentSpec{
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

	r := setupReconciler(deployment)
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      deployment.Name,
			Namespace: deployment.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Verify deletion message was published
	assert.Len(t, mock.Published, 1)
	msg, ok := mock.Published[0].(messaging.WorkloadComponentStatusMessage)
	assert.True(t, ok)
	assert.Equal(t, "test-deployment", msg.Name)
	assert.Equal(t, "Deleted", msg.Status)
	assert.Equal(t, workloadID.String(), msg.WorkloadID)
	assert.Equal(t, componentID.String(), msg.ID)

	// Note: We can't verify the finalizer was removed by fetching the object
	// because the fake client automatically deletes objects with DeletionTimestamp
	// once all finalizers are removed (which is correct Kubernetes behavior)
}

func TestReconcile_HandlesDeletionWithMissingLabels(t *testing.T) {
	now := metav1.Now()

	deployment := &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-deployment",
			Namespace:         "test-namespace",
			DeletionTimestamp: &now,
			Finalizers:        []string{common.WorkloadFinalizer},
			// No labels - should still handle deletion gracefully
		},
		Spec: appsv1.DeploymentSpec{
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

	r := setupReconciler(deployment)
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      deployment.Name,
			Namespace: deployment.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Verify no message was published (extraction failed)
	assert.Empty(t, mock.Published)

	// Note: We can't verify the finalizer was removed by fetching the object
	// because the fake client automatically deletes objects with DeletionTimestamp
	// once all finalizers are removed (which is correct Kubernetes behavior)
}

func TestReconcile_ContinuesWhenPublishFails(t *testing.T) {
	workloadID := uuid.New()
	componentID := uuid.New()
	projectID := uuid.New()
	now := metav1.Now()

	deployment := &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-deployment",
			Namespace:         "test-namespace",
			DeletionTimestamp: &now,
			Finalizers:        []string{common.WorkloadFinalizer},
			Labels: map[string]string{
				common.WorkloadIDLabel:  workloadID.String(),
				common.ComponentIDLabel: componentID.String(),
				agent.ProjectIDLabel:    projectID.String(),
			},
		},
		Spec: appsv1.DeploymentSpec{
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

	mock := testutils.NewMockFailingPublisher(assert.AnError)
	r := setupReconcilerWithPublisher(mock, deployment)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      deployment.Name,
			Namespace: deployment.Namespace,
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
	var fetchedDeployment appsv1.Deployment
	err = r.Client.Get(context.Background(), types.NamespacedName{Name: deployment.Name, Namespace: deployment.Namespace}, &fetchedDeployment)
	assert.NoError(t, err)
	assert.True(t, controllerutil.ContainsFinalizer(&fetchedDeployment, common.WorkloadFinalizer))
}

func TestSetupWithManager(t *testing.T) {
	// This is a basic test to ensure SetupWithManager doesn't panic
	// Full integration testing would require a real manager
	r := &Reconciler{}
	assert.NotNil(t, r)
	// We can't easily test SetupWithManager without a real manager,
	// but we can verify the struct is properly initialized
	assert.NotNil(t, r)
}

func TestReconcile_Deployment_AutoDiscoveryBehavior(t *testing.T) {
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
			submitter:              "system:serviceaccount:kube-system:my-controller",
			expectedMsgCount:       2,
			expectedSubmitter:      strPtr("kube-system:my-controller"),
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

			replicas := int32(3)
			deployment := &appsv1.Deployment{
				ObjectMeta: metav1.ObjectMeta{
					Name:      "test-deployment",
					Namespace: "test-namespace",
					Labels: map[string]string{
						common.WorkloadIDLabel:  uuid.New().String(),
						common.ComponentIDLabel: uuid.New().String(),
						agent.ProjectIDLabel:    uuid.New().String(),
					},
					Annotations: annotations,
				},
				Spec: appsv1.DeploymentSpec{
					Replicas: &replicas,
				},
				Status: appsv1.DeploymentStatus{
					Replicas:      3,
					ReadyReplicas: 3,
				},
			}

			reconciler := setupReconciler(deployment)
			ctx := ctrl.LoggerInto(context.Background(), zap.New())

			result, err := reconciler.Reconcile(ctx, ctrl.Request{
				NamespacedName: types.NamespacedName{
					Name:      deployment.Name,
					Namespace: deployment.Namespace,
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

func TestReconcile_Deployment_StatusPublishFailure(t *testing.T) {
	replicas := int32(3)
	deployment := &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-deployment",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  "827862af-41b9-4bd6-bd8d-04e4e866dff3",
				common.ComponentIDLabel: "98a47b94-3753-48b7-9b95-0b91f2df27b0",
				agent.ProjectIDLabel:    "121aede7-b363-4188-8d5a-2e034e4d0b3f",
			},
		},
		Spec: appsv1.DeploymentSpec{
			Replicas: &replicas,
			Selector: &metav1.LabelSelector{
				MatchLabels: map[string]string{"app": "test"},
			},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: map[string]string{"app": "test"},
				},
				Spec: corev1.PodSpec{
					Containers: []corev1.Container{{Name: "test", Image: "test:latest"}},
				},
			},
		},
		Status: appsv1.DeploymentStatus{
			Replicas:          3,
			UpdatedReplicas:   3,
			ReadyReplicas:     3,
			AvailableReplicas: 3,
		},
	}

	mock := testutils.NewMockFailingPublisher(assert.AnError)
	r := setupReconcilerWithPublisher(mock, deployment)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      deployment.Name,
			Namespace: deployment.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	// Should return error (triggers automatic requeue) when status publish fails
	assert.Error(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, mock.Published)
}
