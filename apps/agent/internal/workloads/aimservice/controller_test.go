// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package aimservice

import (
	"context"
	"errors"
	"testing"

	aimv1alpha1 "github.com/amd-enterprise-ai/aim-engine/api/v1alpha1"
	"github.com/google/uuid"
	agent "github.com/silogen/agent/internal/common"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
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

// Tests use v1alpha1-typed objects because the reconciler uses the v1alpha1
// typed client (see controller.go for why). There is intentionally no v1alpha2
// variant of these tests: the fake client keys objects by exact GroupVersion
// and does not emulate the API server's None-strategy cross-version serving, so
// a v1alpha2-stored object is simply "not found" when fetched as v1alpha1 here.
// In production the API server does serve v1alpha2-created objects through the
// v1alpha1 endpoint (identical Spec/Status schemas, apiVersion relabeled), so
// the reconciler does handle both — but that guarantee belongs to Kubernetes
// and can only be exercised with envtest (a real API server + CRD), not the
// fake client. The dual-version surface that IS faithfully testable here lives
// in the webhook tests, which decode each version directly.
func setupReconcilerWithPublisher(publisher messaging.MessagePublisher, objs ...client.Object) *Reconciler {
	scheme := runtime.NewScheme()
	_ = aimv1alpha1.AddToScheme(scheme)

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
			Name:      "nonexistent-aimservice",
			Namespace: "test-namespace",
		},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, mock.Published)
}

func TestReconcile_AddsFinalizerToNewResource(t *testing.T) {
	aimService := &aimv1alpha1.AIMService{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-aimservice",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  uuid.New().String(),
				common.ComponentIDLabel: uuid.New().String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
		Status: aimv1alpha1.AIMServiceStatus{
			Status: "Running",
		},
	}

	r := setupReconciler(aimService)
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{Name: aimService.Name, Namespace: aimService.Namespace},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Verify finalizer was added
	var updated aimv1alpha1.AIMService
	err = r.Client.Get(context.Background(), req.NamespacedName, &updated)
	assert.NoError(t, err)
	assert.True(t, controllerutil.ContainsFinalizer(&updated, common.WorkloadFinalizer))

	// Verify status message was published
	assert.Len(t, mock.Published, 1)
	statusMsg, ok := mock.Published[0].(*common.WorkloadComponentStatusMessage)
	assert.True(t, ok)
	assert.NotEmpty(t, statusMsg.Status)
}

func TestReconcile_DoesNotDuplicateFinalizer(t *testing.T) {
	aimService := &aimv1alpha1.AIMService{
		ObjectMeta: metav1.ObjectMeta{
			Name:       "test-aimservice",
			Namespace:  "test-namespace",
			Finalizers: []string{common.WorkloadFinalizer},
			Labels: map[string]string{
				common.WorkloadIDLabel:  uuid.New().String(),
				common.ComponentIDLabel: uuid.New().String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
		Status: aimv1alpha1.AIMServiceStatus{
			Status: "Running",
		},
	}

	r := setupReconciler(aimService)
	mock := r.Publisher.(*testutils.MockPublisher)

	req := reconcile.Request{
		NamespacedName: types.NamespacedName{Name: aimService.Name, Namespace: aimService.Namespace},
	}

	result, err := r.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	var updated aimv1alpha1.AIMService
	err = r.Client.Get(context.Background(), req.NamespacedName, &updated)
	assert.NoError(t, err)
	assert.Len(t, updated.GetFinalizers(), 1)

	// Verify status message was published
	assert.Len(t, mock.Published, 1)
	statusMsg, ok := mock.Published[0].(*common.WorkloadComponentStatusMessage)
	assert.True(t, ok)
	assert.NotEmpty(t, statusMsg.Status)
}

func TestReconcile_SkipsWithoutRequiredLabels(t *testing.T) {
	aimService := &aimv1alpha1.AIMService{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-aimservice",
			Namespace: "test-namespace",
			// No labels - should skip processing
		},
		Status: aimv1alpha1.AIMServiceStatus{
			Status: "Running",
		},
	}

	r := setupReconciler(aimService)
	mock := r.Publisher.(*testutils.MockPublisher)

	result, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: aimService.Name, Namespace: aimService.Namespace},
	})

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, mock.Published)
}

func TestReconcile_HandlesDeletionWithValidLabels(t *testing.T) {
	workloadID := uuid.New()
	componentID := uuid.New()
	projectID := uuid.New()
	now := metav1.Now()

	aimService := &aimv1alpha1.AIMService{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-aimservice",
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

	r := setupReconciler(aimService)
	mock := r.Publisher.(*testutils.MockPublisher)

	result, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: aimService.Name, Namespace: aimService.Namespace},
	})

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Len(t, mock.Published, 1)

	msg, ok := mock.Published[0].(common.WorkloadComponentStatusMessage)
	assert.True(t, ok)
	assert.Equal(t, "test-aimservice", msg.Name)
	assert.Equal(t, "Deleted", msg.Status)
	assert.Equal(t, workloadID.String(), msg.WorkloadID)
	assert.Equal(t, componentID.String(), msg.ID)
}

// Regression guard for the v1alpha1→v1alpha2 migration trap. An AIMService
// created before the migration may still carry spec.template (a v1alpha1-only
// field that v1alpha2 CEL rejects). The reconciler must still be able to drop
// its finalizer so K8s can GC the object — using the v1alpha1 typed client is
// what makes this safe in production. The fake client does not evaluate CRD
// CEL, so this test guards the data-shape contract rather than the CEL
// rejection itself.
func TestReconcile_HandlesDeletionOfLegacyTemplateSpec(t *testing.T) {
	workloadID := uuid.New()
	componentID := uuid.New()
	projectID := uuid.New()
	now := metav1.Now()

	aimService := &aimv1alpha1.AIMService{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "stuck-legacy-template",
			Namespace:         "test-namespace",
			DeletionTimestamp: &now,
			Finalizers:        []string{common.WorkloadFinalizer},
			Labels: map[string]string{
				common.WorkloadIDLabel:  workloadID.String(),
				common.ComponentIDLabel: componentID.String(),
				agent.ProjectIDLabel:    projectID.String(),
			},
		},
		Spec: aimv1alpha1.AIMServiceSpec{
			Template: &aimv1alpha1.AIMServiceTemplateConfig{Name: "legacy-template"},
			Model:    &aimv1alpha1.AIMServiceModel{Name: testutils.Ptr("legacy-model")},
		},
	}

	r := setupReconciler(aimService)
	key := types.NamespacedName{Name: aimService.Name, Namespace: aimService.Namespace}

	_, err := r.Reconcile(context.Background(), reconcile.Request{NamespacedName: key})
	require.NoError(t, err)

	// Success means the finalizer is gone: either the object was garbage-collected
	// (fake client behavior after the last finalizer is removed) or it still exists
	// without the workload finalizer.
	var updated aimv1alpha1.AIMService
	err = r.Client.Get(context.Background(), key, &updated)
	if err == nil {
		assert.False(t, controllerutil.ContainsFinalizer(&updated, common.WorkloadFinalizer))
	} else {
		assert.True(t, apierrors.IsNotFound(err), "unexpected error: %v", err)
	}
}

func TestReconcile_HandlesDeletionWithMissingLabels(t *testing.T) {
	now := metav1.Now()

	aimService := &aimv1alpha1.AIMService{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-aimservice",
			Namespace:         "test-namespace",
			DeletionTimestamp: &now,
			Finalizers:        []string{common.WorkloadFinalizer},
			// No labels - should still handle deletion gracefully
		},
	}

	r := setupReconciler(aimService)
	mock := r.Publisher.(*testutils.MockPublisher)

	result, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: aimService.Name, Namespace: aimService.Namespace},
	})

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, mock.Published)
}

func TestReconcile_DeletionPublishFailure_ReturnsError(t *testing.T) {
	now := metav1.Now()

	aimService := &aimv1alpha1.AIMService{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-aimservice",
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
	r := setupReconcilerWithPublisher(testutils.NewMockFailingPublisher(pubErr), aimService)

	_, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: aimService.Name, Namespace: aimService.Namespace},
	})

	assert.Error(t, err)
	assert.ErrorIs(t, err, pubErr)
}

func TestReconcile_PublishesAutoDiscoveryMessage(t *testing.T) {
	submitter := "system:serviceaccount:ns:my-sa"
	aimService := &aimv1alpha1.AIMService{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-aimservice",
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
		Status: aimv1alpha1.AIMServiceStatus{
			Status: "Running",
		},
	}

	r := setupReconciler(aimService)
	mock := r.Publisher.(*testutils.MockPublisher)

	result, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: aimService.Name, Namespace: aimService.Namespace},
	})

	require.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	require.Len(t, mock.Published, 2)

	autoMsg, ok := mock.Published[0].(*common.AutoDiscoveredWorkloadComponentMessage)
	require.True(t, ok)
	assert.Equal(t, aimService.Name, autoMsg.Name)
	assert.NotNil(t, autoMsg.Submitter)
	assert.Contains(t, *autoMsg.Submitter, "ns:my-sa")

	statusMsg, ok := mock.Published[1].(*common.WorkloadComponentStatusMessage)
	require.True(t, ok)
	assert.NotEmpty(t, statusMsg.Status)
}

func TestReconcile_AutoDiscoveryPublishFailure_ReturnsError(t *testing.T) {
	aimService := &aimv1alpha1.AIMService{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-aimservice",
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
		Status: aimv1alpha1.AIMServiceStatus{
			Status: "Running",
		},
	}

	pubErr := errors.New("auto-discovery publish failed")
	publisher := testutils.NewMockSelectiveFailingPublisher(func(message interface{}) bool {
		_, ok := message.(*common.AutoDiscoveredWorkloadComponentMessage)
		return ok
	}, pubErr)
	r := setupReconcilerWithPublisher(publisher, aimService)

	_, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: aimService.Name, Namespace: aimService.Namespace},
	})
	assert.Error(t, err)
	assert.ErrorIs(t, err, pubErr)
	assert.Empty(t, publisher.Published)
}

func TestReconcile_SkipsPublishingWhenStatusIsEmpty(t *testing.T) {
	aimService := &aimv1alpha1.AIMService{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-aimservice",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  uuid.New().String(),
				common.ComponentIDLabel: uuid.New().String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
		Status: aimv1alpha1.AIMServiceStatus{
			Status: "", // Empty status
		},
	}

	r := setupReconciler(aimService)
	mock := r.Publisher.(*testutils.MockPublisher)

	result, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: aimService.Name, Namespace: aimService.Namespace},
	})

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	// Should not publish any messages when status is empty
	assert.Empty(t, mock.Published)
}

func TestReconcile_StatusPublishFailure_ReturnsError(t *testing.T) {
	aimService := &aimv1alpha1.AIMService{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-aimservice",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  uuid.New().String(),
				common.ComponentIDLabel: uuid.New().String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
		Status: aimv1alpha1.AIMServiceStatus{
			Status: "Running",
		},
	}

	pubErr := errors.New("status publish failed")
	publisher := testutils.NewMockSelectiveFailingPublisher(func(message interface{}) bool {
		_, ok := message.(*common.WorkloadComponentStatusMessage)
		return ok
	}, pubErr)
	r := setupReconcilerWithPublisher(publisher, aimService)

	_, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: aimService.Name, Namespace: aimService.Namespace},
	})
	assert.Error(t, err)
	assert.ErrorIs(t, err, pubErr)
}
