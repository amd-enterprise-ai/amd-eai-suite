// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package statefulset

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
			Name:      "nonexistent-statefulset",
			Namespace: "test-namespace",
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, mock.Published)
}

func TestReconcile_AddsFinalizerToNewResource(t *testing.T) {
	replicas := int32(3)
	sts := &appsv1.StatefulSet{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-statefulset",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  uuid.New().String(),
				common.ComponentIDLabel: uuid.New().String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
		Spec: appsv1.StatefulSetSpec{
			Replicas: &replicas,
			Selector: &metav1.LabelSelector{MatchLabels: map[string]string{"app": "test"}},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{Labels: map[string]string{"app": "test"}},
			},
		},
		Status: appsv1.StatefulSetStatus{
			CurrentReplicas:   3,
			ReadyReplicas:     3,
			AvailableReplicas: 3,
		},
	}

	r := setupReconciler(sts)
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      sts.Name,
			Namespace: sts.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Verify finalizer was added
	var updatedSTS appsv1.StatefulSet
	err = r.Client.Get(context.Background(), req.NamespacedName, &updatedSTS)
	assert.NoError(t, err)
	assert.True(t, controllerutil.ContainsFinalizer(&updatedSTS, common.WorkloadFinalizer))

	// Verify status message was published
	assert.Len(t, mock.Published, 1)
	statusMsg, ok := mock.Published[0].(*messaging.WorkloadComponentStatusMessage)
	assert.True(t, ok)
	assert.NotEmpty(t, statusMsg.Status)
}

func TestReconcile_DoesNotDuplicateFinalizer(t *testing.T) {
	replicas := int32(3)
	sts := &appsv1.StatefulSet{
		ObjectMeta: metav1.ObjectMeta{
			Name:       "test-statefulset",
			Namespace:  "test-namespace",
			Finalizers: []string{common.WorkloadFinalizer},
			Labels: map[string]string{
				common.WorkloadIDLabel:  uuid.New().String(),
				common.ComponentIDLabel: uuid.New().String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
		Spec: appsv1.StatefulSetSpec{
			Replicas: &replicas,
			Selector: &metav1.LabelSelector{MatchLabels: map[string]string{"app": "test"}},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{Labels: map[string]string{"app": "test"}},
			},
		},
		Status: appsv1.StatefulSetStatus{
			CurrentReplicas:   3,
			ReadyReplicas:     3,
			AvailableReplicas: 3,
		},
	}

	r := setupReconciler(sts)
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      sts.Name,
			Namespace: sts.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Verify only one finalizer exists
	var updatedSTS appsv1.StatefulSet
	err = r.Client.Get(context.Background(), req.NamespacedName, &updatedSTS)
	assert.NoError(t, err)
	assert.Len(t, updatedSTS.GetFinalizers(), 1)

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
	replicas := int32(3)

	sts := &appsv1.StatefulSet{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-statefulset",
			Namespace:         "test-namespace",
			DeletionTimestamp: &now,
			Finalizers:        []string{common.WorkloadFinalizer},
			Labels: map[string]string{
				common.WorkloadIDLabel:  workloadID.String(),
				common.ComponentIDLabel: componentID.String(),
				agent.ProjectIDLabel:    projectID.String(),
			},
		},
		Spec: appsv1.StatefulSetSpec{
			Replicas: &replicas,
			Selector: &metav1.LabelSelector{MatchLabels: map[string]string{"app": "test"}},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{Labels: map[string]string{"app": "test"}},
			},
		},
	}

	r := setupReconciler(sts)
	mock := r.Publisher.(*testutils.MockPublisher)

	result, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: sts.Name, Namespace: sts.Namespace},
	})

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Len(t, mock.Published, 1)

	msg, ok := mock.Published[0].(messaging.WorkloadComponentStatusMessage)
	assert.True(t, ok)
	assert.Equal(t, "test-statefulset", msg.Name)
	assert.Equal(t, "Deleted", msg.Status)
	assert.Equal(t, workloadID.String(), msg.WorkloadID)
	assert.Equal(t, componentID.String(), msg.ID)
}

func TestReconcile_HandlesDeletionWithMissingLabels(t *testing.T) {
	now := metav1.Now()
	replicas := int32(3)

	sts := &appsv1.StatefulSet{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-statefulset",
			Namespace:         "test-namespace",
			DeletionTimestamp: &now,
			Finalizers:        []string{common.WorkloadFinalizer},
			// No labels - should still handle deletion gracefully
		},
		Spec: appsv1.StatefulSetSpec{
			Replicas: &replicas,
			Selector: &metav1.LabelSelector{MatchLabels: map[string]string{"app": "test"}},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{Labels: map[string]string{"app": "test"}},
			},
		},
	}

	r := setupReconciler(sts)
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      sts.Name,
			Namespace: sts.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, mock.Published)
}

func TestReconcile_ContinuesWhenPublishFails(t *testing.T) {
	workloadID := uuid.New()
	componentID := uuid.New()
	projectID := uuid.New()
	now := metav1.Now()
	replicas := int32(3)

	sts := &appsv1.StatefulSet{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-statefulset",
			Namespace:         "test-namespace",
			DeletionTimestamp: &now,
			Finalizers:        []string{common.WorkloadFinalizer},
			Labels: map[string]string{
				common.WorkloadIDLabel:  workloadID.String(),
				common.ComponentIDLabel: componentID.String(),
				agent.ProjectIDLabel:    projectID.String(),
			},
		},
		Spec: appsv1.StatefulSetSpec{
			Replicas: &replicas,
			Selector: &metav1.LabelSelector{MatchLabels: map[string]string{"app": "test"}},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{Labels: map[string]string{"app": "test"}},
			},
		},
	}

	mock := testutils.NewMockFailingPublisher(assert.AnError)
	r := setupReconcilerWithPublisher(mock, sts)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      sts.Name,
			Namespace: sts.Namespace,
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
	var fetchedSTS appsv1.StatefulSet
	err = r.Client.Get(context.Background(), types.NamespacedName{Name: sts.Name, Namespace: sts.Namespace}, &fetchedSTS)
	assert.NoError(t, err)
	assert.True(t, controllerutil.ContainsFinalizer(&fetchedSTS, common.WorkloadFinalizer))
}

func TestSetupWithManager(t *testing.T) {
	r := &Reconciler{}
	assert.NotNil(t, r)
}

func TestReconcile_StatefulSet_AutoDiscovered_WithSubmitter(t *testing.T) {
	replicas := int32(3)
	sts := &appsv1.StatefulSet{
		TypeMeta: metav1.TypeMeta{
			Kind:       "StatefulSet",
			APIVersion: "apps/v1",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-statefulset",
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
		Spec: appsv1.StatefulSetSpec{
			Replicas: &replicas,
		},
		Status: appsv1.StatefulSetStatus{
			CurrentReplicas:   3,
			ReadyReplicas:     3,
			AvailableReplicas: 3,
		},
	}

	reconciler := setupReconciler(sts)
	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "test-statefulset",
			Namespace: "test-namespace",
		},
	})

	require.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	mockPub := reconciler.Publisher.(*testutils.MockPublisher)
	require.Len(t, mockPub.Published, 2)

	autoDiscMsg, ok := mockPub.Published[0].(*messaging.AutoDiscoveredWorkloadComponentMessage)
	require.True(t, ok)
	assert.Equal(t, "121aede7-b363-4188-8d5a-2e034e4d0b3f", autoDiscMsg.ProjectID)
	assert.Equal(t, "827862af-41b9-4bd6-bd8d-04e4e866dff3", autoDiscMsg.WorkloadID)
	assert.Equal(t, "98a47b94-3753-48b7-9b95-0b91f2df27b0", autoDiscMsg.ComponentID)
	assert.Equal(t, "test-statefulset", autoDiscMsg.Name)
	assert.NotNil(t, autoDiscMsg.Submitter)
	assert.Equal(t, "kube-system:my-controller", *autoDiscMsg.Submitter)

	statusMsg, ok := mockPub.Published[1].(*messaging.WorkloadComponentStatusMessage)
	require.True(t, ok)
	assert.Equal(t, "Running", statusMsg.Status)
}

func TestReconcile_StatefulSet_AutoDiscovered_WithoutSubmitter(t *testing.T) {
	replicas := int32(3)
	sts := &appsv1.StatefulSet{
		TypeMeta: metav1.TypeMeta{
			Kind:       "StatefulSet",
			APIVersion: "apps/v1",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-statefulset",
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
		Spec: appsv1.StatefulSetSpec{
			Replicas: &replicas,
		},
		Status: appsv1.StatefulSetStatus{
			CurrentReplicas:   3,
			ReadyReplicas:     3,
			AvailableReplicas: 3,
		},
	}

	reconciler := setupReconciler(sts)
	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "test-statefulset",
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

func TestReconcile_StatefulSet_StatusPublishFailure(t *testing.T) {
	replicas := int32(3)
	sts := &appsv1.StatefulSet{
		TypeMeta: metav1.TypeMeta{
			Kind:       "StatefulSet",
			APIVersion: "apps/v1",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-statefulset",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  "827862af-41b9-4bd6-bd8d-04e4e866dff3",
				common.ComponentIDLabel: "98a47b94-3753-48b7-9b95-0b91f2df27b0",
				agent.ProjectIDLabel:    "121aede7-b363-4188-8d5a-2e034e4d0b3f",
			},
		},
		Spec: appsv1.StatefulSetSpec{
			Replicas: &replicas,
		},
		Status: appsv1.StatefulSetStatus{
			CurrentReplicas:   3,
			ReadyReplicas:     3,
			AvailableReplicas: 3,
		},
	}

	mock := testutils.NewMockFailingPublisher(assert.AnError)
	r := setupReconcilerWithPublisher(mock, sts)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{
			Name:      sts.Name,
			Namespace: sts.Namespace,
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.Error(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, mock.Published)
}

func TestReconcile_StatefulSet_NotAutoDiscovered(t *testing.T) {
	replicas := int32(3)
	sts := &appsv1.StatefulSet{
		TypeMeta: metav1.TypeMeta{
			Kind:       "StatefulSet",
			APIVersion: "apps/v1",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-statefulset",
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
		Spec: appsv1.StatefulSetSpec{
			Replicas: &replicas,
		},
		Status: appsv1.StatefulSetStatus{
			CurrentReplicas:   3,
			ReadyReplicas:     3,
			AvailableReplicas: 3,
		},
	}

	reconciler := setupReconciler(sts)
	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "test-statefulset",
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
