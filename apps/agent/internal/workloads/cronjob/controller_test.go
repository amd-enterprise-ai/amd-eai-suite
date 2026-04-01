// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package cronjob

import (
	"context"
	"testing"

	"github.com/google/uuid"
	agent "github.com/silogen/agent/internal/common"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	batchv1 "k8s.io/api/batch/v1"
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
	_ = batchv1.AddToScheme(scheme)

	fakeClient := fake.NewClientBuilder().WithScheme(scheme).WithObjects(objs...).Build()
	return &Reconciler{Client: fakeClient, Publisher: publisher}
}

func TestReconcile_AddsFinalizer(t *testing.T) {
	scheme := runtime.NewScheme()
	_ = batchv1.AddToScheme(scheme)

	cj := &batchv1.CronJob{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-cronjob",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  uuid.New().String(),
				common.ComponentIDLabel: uuid.New().String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
		Spec: batchv1.CronJobSpec{
			Schedule: "*/5 * * * *",
			JobTemplate: batchv1.JobTemplateSpec{
				Spec: batchv1.JobSpec{
					Template: corev1.PodTemplateSpec{
						Spec: corev1.PodSpec{
							Containers: []corev1.Container{{Name: "test", Image: "test:latest"}},
						},
					},
				},
			},
		},
	}

	r := setupReconciler(cj)

	result, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: cj.Name, Namespace: cj.Namespace},
	})

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	var updated batchv1.CronJob
	_ = r.Client.Get(context.Background(), types.NamespacedName{Name: cj.Name, Namespace: cj.Namespace}, &updated)
	assert.True(t, controllerutil.ContainsFinalizer(&updated, common.WorkloadFinalizer))
}

func TestReconcile_HandlesDeletion(t *testing.T) {
	scheme := runtime.NewScheme()
	_ = batchv1.AddToScheme(scheme)

	workloadID := uuid.New()
	componentID := uuid.New()
	now := metav1.Now()

	cj := &batchv1.CronJob{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-cronjob",
			Namespace:         "test-namespace",
			DeletionTimestamp: &now,
			Finalizers:        []string{common.WorkloadFinalizer},
			Labels: map[string]string{
				common.WorkloadIDLabel:  workloadID.String(),
				common.ComponentIDLabel: componentID.String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
		Spec: batchv1.CronJobSpec{
			Schedule: "*/5 * * * *",
			JobTemplate: batchv1.JobTemplateSpec{
				Spec: batchv1.JobSpec{
					Template: corev1.PodTemplateSpec{
						Spec: corev1.PodSpec{
							Containers: []corev1.Container{{Name: "test", Image: "test:latest"}},
						},
					},
				},
			},
		},
	}

	r := setupReconciler(cj)
	mock := r.Publisher.(*testutils.MockPublisher)

	result, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: cj.Name, Namespace: cj.Namespace},
	})

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Len(t, mock.Published, 1)

	msg, ok := mock.Published[0].(messaging.WorkloadComponentStatusMessage)
	assert.True(t, ok)
	assert.Equal(t, "test-cronjob", msg.Name)
	assert.Equal(t, "Deleted", msg.Status)
	assert.Equal(t, workloadID.String(), msg.WorkloadID)
}

func TestReconcile_CronJob_AutoDiscoveryBehavior(t *testing.T) {
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
			submitter:              "system:serviceaccount:default:cronjob-creator",
			expectedMsgCount:       2,
			expectedSubmitter:      strPtr("default:cronjob-creator"),
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

			cronJob := &batchv1.CronJob{
				ObjectMeta: metav1.ObjectMeta{
					Name:      "test-cronjob",
					Namespace: "test-namespace",
					Labels: map[string]string{
						common.WorkloadIDLabel:  uuid.New().String(),
						common.ComponentIDLabel: uuid.New().String(),
						agent.ProjectIDLabel:    uuid.New().String(),
					},
					Annotations: annotations,
				},
				Spec: batchv1.CronJobSpec{
					Schedule: "*/5 * * * *",
				},
				Status: batchv1.CronJobStatus{
					Active: []corev1.ObjectReference{},
				},
			}

			reconciler := setupReconciler(cronJob)
			ctx := ctrl.LoggerInto(context.Background(), zap.New())

			result, err := reconciler.Reconcile(ctx, ctrl.Request{
				NamespacedName: types.NamespacedName{
					Name:      cronJob.Name,
					Namespace: cronJob.Namespace,
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
				assert.Equal(t, "Ready", statusMsg.Status)
			} else {
				statusMsg, ok := mockPub.Published[0].(*messaging.WorkloadComponentStatusMessage)
				require.True(t, ok)
				assert.Equal(t, "Ready", statusMsg.Status)
			}
		})
	}
}

func strPtr(s string) *string {
	return &s
}

func TestReconcile_CronJob_StatusPublishFailure(t *testing.T) {
	scheme := runtime.NewScheme()
	_ = batchv1.AddToScheme(scheme)

	cronJob := &batchv1.CronJob{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-cronjob",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  "827862af-41b9-4bd6-bd8d-04e4e866dff3",
				common.ComponentIDLabel: "98a47b94-3753-48b7-9b95-0b91f2df27b0",
				agent.ProjectIDLabel:    "121aede7-b363-4188-8d5a-2e034e4d0b3f",
			},
		},
		Spec: batchv1.CronJobSpec{
			Schedule: "* * * * *",
			JobTemplate: batchv1.JobTemplateSpec{
				Spec: batchv1.JobSpec{
					Template: corev1.PodTemplateSpec{
						Spec: corev1.PodSpec{
							Containers: []corev1.Container{{Name: "test", Image: "test:latest"}},
						},
					},
				},
			},
		},
	}

	mock := testutils.NewMockFailingPublisher(assert.AnError)
	r := setupReconcilerWithPublisher(mock, cronJob)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      cronJob.Name,
			Namespace: cronJob.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	// Should return error (triggers automatic requeue) when status publish fails
	assert.Error(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, mock.Published)
}

func TestReconcile_CronJob_WithoutRequiredLabels(t *testing.T) {
	scheme := runtime.NewScheme()
	_ = batchv1.AddToScheme(scheme)

	cronJob := &batchv1.CronJob{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-cronjob",
			Namespace: "test-namespace",
		},
		Spec: batchv1.CronJobSpec{
			Schedule: "*/5 * * * *",
			JobTemplate: batchv1.JobTemplateSpec{
				Spec: batchv1.JobSpec{
					Template: corev1.PodTemplateSpec{
						Spec: corev1.PodSpec{
							Containers: []corev1.Container{{Name: "test", Image: "test:latest"}},
						},
					},
				},
			},
		},
	}

	r := setupReconciler(cronJob)
	mock := r.Publisher.(*testutils.MockPublisher)

	ctx := ctrl.LoggerInto(context.Background(), zap.New())
	result, err := r.Reconcile(ctx, reconcile.Request{
		NamespacedName: types.NamespacedName{Name: cronJob.Name, Namespace: cronJob.Namespace},
	})

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, mock.Published)
}

func TestReconcile_CronJob_AutoDiscoveryPublishFailure(t *testing.T) {
	scheme := runtime.NewScheme()
	_ = batchv1.AddToScheme(scheme)

	cronJob := &batchv1.CronJob{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-cronjob",
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
		Spec: batchv1.CronJobSpec{
			Schedule: "*/5 * * * *",
			JobTemplate: batchv1.JobTemplateSpec{
				Spec: batchv1.JobSpec{
					Template: corev1.PodTemplateSpec{
						Spec: corev1.PodSpec{
							Containers: []corev1.Container{{Name: "test", Image: "test:latest"}},
						},
					},
				},
			},
		},
	}

	mock := testutils.NewMockSelectiveFailingPublisher(
		func(msg interface{}) bool {
			_, isAutoDiscovery := msg.(*messaging.AutoDiscoveredWorkloadComponentMessage)
			return isAutoDiscovery
		},
		assert.AnError,
	)
	r := setupReconcilerWithPublisher(mock, cronJob)

	ctx := ctrl.LoggerInto(context.Background(), zap.New())
	result, err := r.Reconcile(ctx, reconcile.Request{
		NamespacedName: types.NamespacedName{Name: cronJob.Name, Namespace: cronJob.Namespace},
	})

	// Auto-discovery failure should now fail reconciliation and trigger requeue
	assert.Error(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, mock.Published)
}
