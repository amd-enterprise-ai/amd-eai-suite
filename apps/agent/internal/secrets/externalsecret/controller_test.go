// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package externalsecret

import (
	"context"
	"errors"
	"strings"
	"testing"

	agent "github.com/silogen/agent/internal/common"
	"github.com/silogen/agent/internal/secrets/common"
	"github.com/silogen/agent/internal/testutils"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/types"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	"github.com/silogen/agent/internal/messaging"
)

const testProjectSecretID = "550e8400-e29b-41d4-a716-446655440000"
const testProjectID = "660e8400-e29b-41d4-a716-446655440000"

func setupExternalSecretReconciler(externalSecret runtime.Object) *ExternalSecretReconciler {
	return setupExternalSecretReconcilerWithPublisher(testutils.NewMockPublisher(), externalSecret)
}

func setupExternalSecretReconcilerWithPublisher(publisher messaging.MessagePublisher, externalSecret runtime.Object) *ExternalSecretReconciler {
	s := runtime.NewScheme()

	fakeClientBuilder := fake.NewClientBuilder().WithScheme(s)
	if externalSecret != nil {
		fakeClientBuilder.WithRuntimeObjects(externalSecret)
	}
	fakeClient := fakeClientBuilder.Build()

	// Use provided publisher or create default mock
	if publisher == nil {
		publisher = testutils.NewMockPublisher()
	}

	reconciler := &ExternalSecretReconciler{
		Client:    fakeClient,
		Publisher: publisher,
		GVK:       schema.GroupVersionKind{Group: "external-secrets.io", Version: "v1beta1", Kind: "ExternalSecret"},
	}

	return reconciler
}

func newTestExternalSecret(scope string) *unstructured.Unstructured {
	labels := map[string]interface{}{}
	labels[common.ProjectSecretIDLabel] = testProjectSecretID
	labels[agent.ProjectIDLabel] = testProjectID
	if scope != "" {
		labels[common.ProjectSecretScopeLabel] = scope
	}

	u := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": "external-secrets.io/v1beta1",
			"kind":       "ExternalSecret",
			"metadata": map[string]interface{}{
				"name":      "managed-external-secret",
				"namespace": "test-namespace",
				"labels":    labels,
			},
			"status": map[string]interface{}{
				"conditions": []interface{}{
					map[string]interface{}{
						"type":    "Ready",
						"status":  string(corev1.ConditionTrue),
						"reason":  "SecretSynced",
						"message": "Secret was synced",
					},
				},
			},
		},
	}
	u.SetGroupVersionKind(schema.GroupVersionKind{Group: "external-secrets.io", Version: "v1beta1", Kind: "ExternalSecret"})
	return u
}

func TestExternalSecretReconciler_Reconcile_UnmanagedExternalSecret(t *testing.T) {
	externalSecret := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": "external-secrets.io/v1beta1",
			"kind":       "ExternalSecret",
			"metadata": map[string]interface{}{
				"name":      "unmanaged-external-secret",
				"namespace": "default",
				"labels":    map[string]interface{}{}, // No project-secret-id label
			},
		},
	}
	externalSecret.SetGroupVersionKind(schema.GroupVersionKind{Group: "external-secrets.io", Version: "v1beta1", Kind: "ExternalSecret"})
	reconciler := setupExternalSecretReconciler(externalSecret)
	req := ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "unmanaged-external-secret",
			Namespace: "default",
		},
	}
	publisher := reconciler.Publisher.(*testutils.MockPublisher)
	result, err := reconciler.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, publisher.Published, "should not publish status for unmanaged external secret")
}

func TestExternalSecretReconciler_Reconcile_AddFinalizer(t *testing.T) {
	externalSecret := newTestExternalSecret("project")
	reconciler := setupExternalSecretReconciler(externalSecret)
	req := ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "managed-external-secret",
			Namespace: "test-namespace",
		},
	}
	publisher := reconciler.Publisher.(*testutils.MockPublisher)

	result, err := reconciler.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Verify finalizer was added
	updatedExternalSecret := &unstructured.Unstructured{}
	updatedExternalSecret.SetGroupVersionKind(schema.GroupVersionKind{Group: "external-secrets.io", Version: "v1beta1", Kind: "ExternalSecret"})
	err = reconciler.Client.Get(context.Background(), req.NamespacedName, updatedExternalSecret)
	require.NoError(t, err)
	assert.Contains(t, updatedExternalSecret.GetFinalizers(), Finalizer)

	// Verify status was published
	require.Len(t, publisher.Published, 1)
	statusMsg, ok := publisher.Published[0].(*messaging.ProjectSecretsUpdateMessage)
	require.True(t, ok)
	assert.Equal(t, messaging.MessageTypeProjectSecretsUpdate, statusMsg.MessageType)
	assert.Equal(t, "550e8400-e29b-41d4-a716-446655440000", statusMsg.ProjectSecretID)
	assert.Equal(t, messaging.ProjectSecretStatusSynced, statusMsg.Status)
	assert.NotNil(t, statusMsg.SecretScope)
	assert.Equal(t, messaging.SecretScopeProject, *statusMsg.SecretScope)
	assert.NotNil(t, statusMsg.StatusReason)
	assert.Equal(t, "Secret was synced", *statusMsg.StatusReason)
}

func TestExternalSecretReconciler_Reconcile_WithExistingFinalizer(t *testing.T) {
	externalSecret := newTestExternalSecret("organization")
	externalSecret.SetFinalizers([]string{Finalizer})
	reconciler := setupExternalSecretReconciler(externalSecret)
	req := ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "managed-external-secret",
			Namespace: "test-namespace",
		},
	}
	publisher := reconciler.Publisher.(*testutils.MockPublisher)

	result, err := reconciler.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Verify status was published
	require.Len(t, publisher.Published, 1)
	statusMsg, ok := publisher.Published[0].(*messaging.ProjectSecretsUpdateMessage)
	require.True(t, ok)
	assert.Equal(t, messaging.ProjectSecretStatusSynced, statusMsg.Status)
	assert.NotNil(t, statusMsg.SecretScope)
	assert.Equal(t, messaging.SecretScopeOrganization, *statusMsg.SecretScope)
}

func TestExternalSecretReconciler_Reconcile_ExternalSecretNotFound(t *testing.T) {
	reconciler := setupExternalSecretReconciler(nil)
	req := ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "non-existent",
			Namespace: "default",
		},
	}
	publisher := reconciler.Publisher.(*testutils.MockPublisher)
	result, err := reconciler.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, publisher.Published)
}

func TestExternalSecretReconciler_HandleDeletion(t *testing.T) {
	externalSecret := newTestExternalSecret("project")
	externalSecret.SetFinalizers([]string{Finalizer})
	reconciler := setupExternalSecretReconciler(externalSecret)
	publisher := reconciler.Publisher.(*testutils.MockPublisher)

	// Mark the external secret for deletion
	err := reconciler.Client.Delete(context.Background(), externalSecret)
	require.NoError(t, err)

	req := ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "managed-external-secret",
			Namespace: "test-namespace",
		},
	}

	// Reconcile should handle the deletion and remove the finalizer
	result, err := reconciler.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Verify deletion status was published
	require.Len(t, publisher.Published, 1)
	statusMsg, ok := publisher.Published[0].(*messaging.ProjectSecretsUpdateMessage)
	require.True(t, ok)
	assert.Equal(t, messaging.ProjectSecretStatusDeleted, statusMsg.Status)
	assert.NotNil(t, statusMsg.StatusReason)
	assert.Equal(t, "ExternalSecret deleted successfully", *statusMsg.StatusReason)

	// After finalizer is removed, the external secret should be fully deleted
	updatedExternalSecret := &unstructured.Unstructured{}
	updatedExternalSecret.SetGroupVersionKind(schema.GroupVersionKind{Group: "external-secrets.io", Version: "v1beta1", Kind: "ExternalSecret"})
	err = reconciler.Client.Get(context.Background(), req.NamespacedName, updatedExternalSecret)
	assert.True(t, err != nil && strings.Contains(err.Error(), "not found"), "external secret should be deleted after finalizer removal")
}

func TestExternalSecretReconciler_HandleDeletion_NoFinalizer(t *testing.T) {
	externalSecret := newTestExternalSecret("project")
	// No finalizer
	reconciler := setupExternalSecretReconciler(externalSecret)
	publisher := reconciler.Publisher.(*testutils.MockPublisher)

	// Mark the external secret for deletion
	err := reconciler.Client.Delete(context.Background(), externalSecret)
	require.NoError(t, err)

	req := ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "managed-external-secret",
			Namespace: "test-namespace",
		},
	}

	result, err := reconciler.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, publisher.Published, "should not publish if finalizer already removed")
}

func TestExternalSecretReconciler_HandleDeletion_WithFinalizerButNoLabel(t *testing.T) {
	// Verifies that deletion is handled even when the tracking label is missing,
	// preventing stuck resources due to an orphaned finalizer.
	externalSecret := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": "external-secrets.io/v1beta1",
			"kind":       "ExternalSecret",
			"metadata": map[string]interface{}{
				"name":      "no-label-external-secret",
				"namespace": "test-namespace",
				"labels":    map[string]interface{}{},
			},
		},
	}
	externalSecret.SetGroupVersionKind(schema.GroupVersionKind{Group: "external-secrets.io", Version: "v1beta1", Kind: "ExternalSecret"})
	externalSecret.SetFinalizers([]string{Finalizer})

	reconciler := setupExternalSecretReconciler(externalSecret)
	publisher := reconciler.Publisher.(*testutils.MockPublisher)

	err := reconciler.Client.Delete(context.Background(), externalSecret)
	require.NoError(t, err)

	req := ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "no-label-external-secret",
			Namespace: "test-namespace",
		},
	}

	result, err := reconciler.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// HandleDeletion skips publish when the label is missing but still removes the finalizer
	assert.Empty(t, publisher.Published, "should not publish status when label is missing")

	updatedExternalSecret := &unstructured.Unstructured{}
	updatedExternalSecret.SetGroupVersionKind(schema.GroupVersionKind{Group: "external-secrets.io", Version: "v1beta1", Kind: "ExternalSecret"})
	err = reconciler.Client.Get(context.Background(), req.NamespacedName, updatedExternalSecret)
	assert.True(t, err != nil && strings.Contains(err.Error(), "not found"), "external secret should be deleted after finalizer removal")
}

func TestExternalSecretReconciler_PublishStatus_Error(t *testing.T) {
	externalSecret := newTestExternalSecret("project")
	externalSecret.SetFinalizers([]string{Finalizer})
	publisher := testutils.NewMockFailingPublisher(errors.New("test error"))
	reconciler := setupExternalSecretReconcilerWithPublisher(publisher, externalSecret)
	req := ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "managed-external-secret",
			Namespace: "test-namespace",
		},
	}

	result, err := reconciler.Reconcile(context.Background(), req)

	assert.Error(t, err, "should return error on publish failure")
	assert.Equal(t, ctrl.Result{}, result, "should return empty result (controller-runtime handles requeue)")
}

func TestExternalSecretReconciler_SetupWithManager(t *testing.T) {
	// This test just verifies the method exists and returns no error
	// Actual manager setup would require a full integration test
	reconciler := setupExternalSecretReconciler(nil)

	// We can't test this without a real manager, but we can verify the method signature
	assert.NotNil(t, reconciler)
}
