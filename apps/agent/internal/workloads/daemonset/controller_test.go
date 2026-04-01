// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package daemonset

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

	fakeClient := fake.NewClientBuilder().WithScheme(scheme).WithObjects(objs...).Build()
	return &Reconciler{Client: fakeClient, Publisher: publisher}
}

func TestReconcile_AddsFinalizer(t *testing.T) {
	ds := &appsv1.DaemonSet{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-daemonset",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  uuid.New().String(),
				common.ComponentIDLabel: uuid.New().String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
		Spec: appsv1.DaemonSetSpec{
			Selector: &metav1.LabelSelector{MatchLabels: map[string]string{"app": "test"}},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{Labels: map[string]string{"app": "test"}},
			},
		},
	}

	r := setupReconciler(ds)

	result, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: ds.Name, Namespace: ds.Namespace},
	})

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	var updated appsv1.DaemonSet
	_ = r.Client.Get(context.Background(), types.NamespacedName{Name: ds.Name, Namespace: ds.Namespace}, &updated)
	assert.True(t, controllerutil.ContainsFinalizer(&updated, common.WorkloadFinalizer))
}

func TestReconcile_HandlesDeletion(t *testing.T) {
	workloadID := uuid.New()
	componentID := uuid.New()
	now := metav1.Now()

	ds := &appsv1.DaemonSet{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-daemonset",
			Namespace:         "test-namespace",
			DeletionTimestamp: &now,
			Finalizers:        []string{common.WorkloadFinalizer},
			Labels: map[string]string{
				common.WorkloadIDLabel:  workloadID.String(),
				common.ComponentIDLabel: componentID.String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
		Spec: appsv1.DaemonSetSpec{
			Selector: &metav1.LabelSelector{MatchLabels: map[string]string{"app": "test"}},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{Labels: map[string]string{"app": "test"}},
			},
		},
	}

	r := setupReconciler(ds)
	mock := r.Publisher.(*testutils.MockPublisher)

	result, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: ds.Name, Namespace: ds.Namespace},
	})

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Len(t, mock.Published, 1)

	msg, ok := mock.Published[0].(messaging.WorkloadComponentStatusMessage)
	assert.True(t, ok)
	assert.Equal(t, "test-daemonset", msg.Name)
	assert.Equal(t, "Deleted", msg.Status)
	assert.Equal(t, workloadID.String(), msg.WorkloadID)
}

func TestReconcile_DaemonSet_AutoDiscoveryBehavior(t *testing.T) {
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
			submitter:              "oidc:admin@example.com",
			expectedMsgCount:       2,
			expectedSubmitter:      strPtr("admin@example.com"),
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

			daemonSet := &appsv1.DaemonSet{
				ObjectMeta: metav1.ObjectMeta{
					Name:      "test-daemonset",
					Namespace: "test-namespace",
					Labels: map[string]string{
						common.WorkloadIDLabel:  uuid.New().String(),
						common.ComponentIDLabel: uuid.New().String(),
						agent.ProjectIDLabel:    uuid.New().String(),
					},
					Annotations: annotations,
				},
				Status: appsv1.DaemonSetStatus{
					DesiredNumberScheduled: 3,
					CurrentNumberScheduled: 3,
					NumberReady:            3,
					NumberAvailable:        3,
				},
			}

			reconciler := setupReconciler(daemonSet)
			ctx := ctrl.LoggerInto(context.Background(), zap.New())

			result, err := reconciler.Reconcile(ctx, ctrl.Request{
				NamespacedName: types.NamespacedName{
					Name:      daemonSet.Name,
					Namespace: daemonSet.Namespace,
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

func TestReconcile_DaemonSet_StatusPublishFailure(t *testing.T) {
	daemonSet := &appsv1.DaemonSet{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-daemonset",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  "827862af-41b9-4bd6-bd8d-04e4e866dff3",
				common.ComponentIDLabel: "98a47b94-3753-48b7-9b95-0b91f2df27b0",
				agent.ProjectIDLabel:    "121aede7-b363-4188-8d5a-2e034e4d0b3f",
			},
		},
		Spec: appsv1.DaemonSetSpec{
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
	}

	mock := testutils.NewMockFailingPublisher(assert.AnError)
	r := setupReconcilerWithPublisher(mock, daemonSet)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      daemonSet.Name,
			Namespace: daemonSet.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	// Should return error (triggers automatic requeue) when status publish fails
	assert.Error(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, mock.Published)
}

func TestReconcile_DaemonSet_WithoutRequiredLabels(t *testing.T) {
	daemonSet := &appsv1.DaemonSet{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-daemonset",
			Namespace: "test-namespace",
		},
		Spec: appsv1.DaemonSetSpec{
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
	}

	r := setupReconciler(daemonSet)
	mock := r.Publisher.(*testutils.MockPublisher)

	ctx := ctrl.LoggerInto(context.Background(), zap.New())
	result, err := r.Reconcile(ctx, reconcile.Request{
		NamespacedName: types.NamespacedName{Name: daemonSet.Name, Namespace: daemonSet.Namespace},
	})

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, mock.Published)
}

func TestReconcile_DaemonSet_AutoDiscoveryPublishFailure(t *testing.T) {
	scheme := runtime.NewScheme()
	_ = appsv1.AddToScheme(scheme)

	daemonSet := &appsv1.DaemonSet{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-daemonset",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  "827862af-41b9-4bd6-bd8d-04e4e866dff3",
				common.ComponentIDLabel: "98a47b94-3753-48b7-9b95-0b91f2df27b0",
				agent.ProjectIDLabel:    "121aede7-b363-4188-8d5a-2e034e4d0b3f",
			},
			Annotations: map[string]string{
				agent.AutoDiscoveredAnnotation: "true",
				agent.SubmitterAnnotation:      "user@example.com",
			},
		},
		Spec: appsv1.DaemonSetSpec{
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
		Status: appsv1.DaemonSetStatus{
			DesiredNumberScheduled: 3,
			CurrentNumberScheduled: 3,
			NumberReady:            3,
			NumberAvailable:        3,
		},
	}

	mock := testutils.NewMockSelectiveFailingPublisher(
		func(msg interface{}) bool {
			_, isAutoDiscovery := msg.(*messaging.AutoDiscoveredWorkloadComponentMessage)
			return isAutoDiscovery
		},
		assert.AnError,
	)
	r := setupReconcilerWithPublisher(mock, daemonSet)

	ctx := ctrl.LoggerInto(context.Background(), zap.New())
	result, err := r.Reconcile(ctx, reconcile.Request{
		NamespacedName: types.NamespacedName{Name: daemonSet.Name, Namespace: daemonSet.Namespace},
	})

	// Auto-discovery failure should now fail reconciliation and trigger requeue
	assert.Error(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, mock.Published)
}
