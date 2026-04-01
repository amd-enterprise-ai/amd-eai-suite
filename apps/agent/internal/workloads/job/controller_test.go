// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package job

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
	_ = corev1.AddToScheme(scheme)

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
			Name:      "nonexistent-job",
			Namespace: "test-namespace",
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, mock.Published)
}

func TestReconcile_AddsFinalizerToNewResource(t *testing.T) {
	job := &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-job",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  uuid.New().String(),
				common.ComponentIDLabel: uuid.New().String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
		Spec: batchv1.JobSpec{
			Template: corev1.PodTemplateSpec{
				Spec: corev1.PodSpec{
					Containers: []corev1.Container{{Name: "test", Image: "test:latest"}},
				},
			},
		},
	}

	r := setupReconciler(job)
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      job.Name,
			Namespace: job.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Verify finalizer was added
	var updatedJob batchv1.Job
	err = r.Client.Get(context.Background(), req.NamespacedName, &updatedJob)
	assert.NoError(t, err)
	assert.True(t, controllerutil.ContainsFinalizer(&updatedJob, common.WorkloadFinalizer))

	// Verify status message was published
	assert.Len(t, mock.Published, 1)
	statusMsg, ok := mock.Published[0].(*messaging.WorkloadComponentStatusMessage)
	assert.True(t, ok)
	assert.NotEmpty(t, statusMsg.Status)
}

func TestReconcile_DoesNotDuplicateFinalizer(t *testing.T) {
	job := &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{
			Name:       "test-job",
			Namespace:  "test-namespace",
			Finalizers: []string{common.WorkloadFinalizer},
			Labels: map[string]string{
				common.WorkloadIDLabel:  uuid.New().String(),
				common.ComponentIDLabel: uuid.New().String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
		Spec: batchv1.JobSpec{
			Template: corev1.PodTemplateSpec{
				Spec: corev1.PodSpec{
					Containers: []corev1.Container{{Name: "test", Image: "test:latest"}},
				},
			},
		},
	}

	r := setupReconciler(job)
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      job.Name,
			Namespace: job.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Verify only one finalizer exists
	var updatedJob batchv1.Job
	err = r.Client.Get(context.Background(), req.NamespacedName, &updatedJob)
	assert.NoError(t, err)
	assert.Len(t, updatedJob.GetFinalizers(), 1)

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

	job := &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-job",
			Namespace:         "test-namespace",
			DeletionTimestamp: &now,
			Finalizers:        []string{common.WorkloadFinalizer},
			Labels: map[string]string{
				common.WorkloadIDLabel:  workloadID.String(),
				common.ComponentIDLabel: componentID.String(),
				agent.ProjectIDLabel:    projectID.String(),
			},
		},
		Spec: batchv1.JobSpec{
			Template: corev1.PodTemplateSpec{
				Spec: corev1.PodSpec{
					Containers: []corev1.Container{{Name: "test", Image: "test:latest"}},
				},
			},
		},
	}

	r := setupReconciler(job)
	mock := r.Publisher.(*testutils.MockPublisher)

	result, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: job.Name, Namespace: job.Namespace},
	})

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Len(t, mock.Published, 1)

	msg, ok := mock.Published[0].(messaging.WorkloadComponentStatusMessage)
	assert.True(t, ok)
	assert.Equal(t, "test-job", msg.Name)
	assert.Equal(t, "Deleted", msg.Status)
	assert.Equal(t, workloadID.String(), msg.WorkloadID)
	assert.Equal(t, componentID.String(), msg.ID)
}

func TestReconcile_HandlesDeletionWithMissingLabels(t *testing.T) {
	now := metav1.Now()

	job := &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-job",
			Namespace:         "test-namespace",
			DeletionTimestamp: &now,
			Finalizers:        []string{common.WorkloadFinalizer},
			// No labels - should still handle deletion gracefully
		},
		Spec: batchv1.JobSpec{
			Template: corev1.PodTemplateSpec{
				Spec: corev1.PodSpec{
					Containers: []corev1.Container{{Name: "test", Image: "test:latest"}},
				},
			},
		},
	}

	r := setupReconciler(job)
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      job.Name,
			Namespace: job.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Verify no message was published (extraction failed)
	assert.Empty(t, mock.Published)
}

func TestReconcile_ContinuesWhenPublishFails(t *testing.T) {
	workloadID := uuid.New()
	componentID := uuid.New()
	projectID := uuid.New()
	now := metav1.Now()

	job := &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-job",
			Namespace:         "test-namespace",
			DeletionTimestamp: &now,
			Finalizers:        []string{common.WorkloadFinalizer},
			Labels: map[string]string{
				common.WorkloadIDLabel:  workloadID.String(),
				common.ComponentIDLabel: componentID.String(),
				agent.ProjectIDLabel:    projectID.String(),
			},
		},
		Spec: batchv1.JobSpec{
			Template: corev1.PodTemplateSpec{
				Spec: corev1.PodSpec{
					Containers: []corev1.Container{{Name: "test", Image: "test:latest"}},
				},
			},
		},
	}

	mock := testutils.NewMockFailingPublisher(assert.AnError)
	r := setupReconcilerWithPublisher(mock, job)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      job.Name,
			Namespace: job.Namespace,
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
	var fetchedJob batchv1.Job
	err = r.Client.Get(context.Background(), types.NamespacedName{Name: job.Name, Namespace: job.Namespace}, &fetchedJob)
	assert.NoError(t, err)
	assert.True(t, controllerutil.ContainsFinalizer(&fetchedJob, common.WorkloadFinalizer))
}

func TestSetupWithManager(t *testing.T) {
	// Basic smoke test to ensure SetupWithManager doesn't panic
	r := &Reconciler{}
	assert.NotNil(t, r)
}

func TestReconcile_Job_AutoDiscovered_WithSubmitter(t *testing.T) {
	jobObj := &batchv1.Job{
		TypeMeta: metav1.TypeMeta{
			Kind:       "Job",
			APIVersion: "batch/v1",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-job",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  "827862af-41b9-4bd6-bd8d-04e4e866dff3",
				common.ComponentIDLabel: "98a47b94-3753-48b7-9b95-0b91f2df27b0",
				agent.ProjectIDLabel:    "121aede7-b363-4188-8d5a-2e034e4d0b3f",
			},
			Annotations: map[string]string{
				agent.AutoDiscoveredAnnotation: "true",
				agent.SubmitterAnnotation:      "system:serviceaccount:kube-system:my-controller",
			},
		},
		Status: batchv1.JobStatus{
			Active: 1,
		},
	}

	reconciler := setupReconciler(jobObj)
	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "test-job",
			Namespace: "test-namespace",
		},
	})

	require.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	mockPub := reconciler.Publisher.(*testutils.MockPublisher)
	require.Len(t, mockPub.Published, 2)

	// First message should be auto-discovery
	autoDiscMsg, ok := mockPub.Published[0].(*messaging.AutoDiscoveredWorkloadComponentMessage)
	require.True(t, ok)
	assert.Equal(t, "121aede7-b363-4188-8d5a-2e034e4d0b3f", autoDiscMsg.ProjectID)
	assert.Equal(t, "827862af-41b9-4bd6-bd8d-04e4e866dff3", autoDiscMsg.WorkloadID)
	assert.Equal(t, "98a47b94-3753-48b7-9b95-0b91f2df27b0", autoDiscMsg.ComponentID)
	assert.Equal(t, "test-job", autoDiscMsg.Name)
	assert.NotNil(t, autoDiscMsg.Submitter)
	assert.Equal(t, "kube-system:my-controller", *autoDiscMsg.Submitter)

	// Second message should be status update
	statusMsg, ok := mockPub.Published[1].(*messaging.WorkloadComponentStatusMessage)
	require.True(t, ok)
	assert.Equal(t, "Running", statusMsg.Status)
}

func TestReconcile_Job_AutoDiscovered_WithoutSubmitter(t *testing.T) {
	jobObj := &batchv1.Job{
		TypeMeta: metav1.TypeMeta{
			Kind:       "Job",
			APIVersion: "batch/v1",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-job",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  "4759c498-818d-4e57-b32d-84631143c86b",
				common.ComponentIDLabel: "91ee48b3-0ac4-4a20-b9b9-d62850f406a2",
				agent.ProjectIDLabel:    "7e0f1c68-f700-4243-b13f-3f19e8f2ee3c",
			},
			Annotations: map[string]string{
				agent.AutoDiscoveredAnnotation: "true",
			},
		},
		Status: batchv1.JobStatus{
			Active: 1,
		},
	}

	reconciler := setupReconciler(jobObj)
	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "test-job",
			Namespace: "test-namespace",
		},
	})

	require.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	mockPub := reconciler.Publisher.(*testutils.MockPublisher)
	require.Len(t, mockPub.Published, 2)

	autoDiscMsg, ok := mockPub.Published[0].(*messaging.AutoDiscoveredWorkloadComponentMessage)
	require.True(t, ok)
	assert.Nil(t, autoDiscMsg.Submitter)

	statusMsg, ok := mockPub.Published[1].(*messaging.WorkloadComponentStatusMessage)
	require.True(t, ok)
	assert.Equal(t, "Running", statusMsg.Status)
}

func TestReconcile_Job_StatusPublishFailure(t *testing.T) {
	jobObj := &batchv1.Job{
		TypeMeta: metav1.TypeMeta{
			Kind:       "Job",
			APIVersion: "batch/v1",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-job",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  "827862af-41b9-4bd6-bd8d-04e4e866dff3",
				common.ComponentIDLabel: "98a47b94-3753-48b7-9b95-0b91f2df27b0",
				agent.ProjectIDLabel:    "121aede7-b363-4188-8d5a-2e034e4d0b3f",
			},
		},
		Status: batchv1.JobStatus{
			Active: 1,
		},
	}

	mock := testutils.NewMockFailingPublisher(assert.AnError)
	r := setupReconcilerWithPublisher(mock, jobObj)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      jobObj.Name,
			Namespace: jobObj.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	// Should return error (triggers automatic requeue) when status publish fails
	assert.Error(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, mock.Published)
}

func TestReconcile_Job_NotAutoDiscovered(t *testing.T) {
	jobObj := &batchv1.Job{
		TypeMeta: metav1.TypeMeta{
			Kind:       "Job",
			APIVersion: "batch/v1",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-job",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  "be684967-17f1-485a-bfa0-94492681ff0f",
				common.ComponentIDLabel: "52c63446-ef36-44a2-97a8-c238ff065ea0",
				agent.ProjectIDLabel:    "c280b019-b1dd-4deb-9afc-709ee93d6a3a",
			},
			Annotations: map[string]string{
				agent.AutoDiscoveredAnnotation: "false",
			},
		},
		Status: batchv1.JobStatus{
			Active: 1,
		},
	}

	reconciler := setupReconciler(jobObj)
	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "test-job",
			Namespace: "test-namespace",
		},
	})

	require.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	mockPub := reconciler.Publisher.(*testutils.MockPublisher)
	require.Len(t, mockPub.Published, 1)

	statusMsg, ok := mockPub.Published[0].(*messaging.WorkloadComponentStatusMessage)
	require.True(t, ok)
	assert.Equal(t, "Running", statusMsg.Status)
}
