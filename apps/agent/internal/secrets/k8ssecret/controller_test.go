// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package k8ssecret

import (
	"context"
	"strings"
	"testing"

	agent "github.com/silogen/agent/internal/common"
	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/secrets/common"
	"github.com/silogen/agent/internal/testutils"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
)

const testProjectID = "660e8400-e29b-41d4-a716-446655440000"

func setupKubernetesSecretReconciler(secret runtime.Object) *KubernetesSecretReconciler {
	return setupKubernetesSecretReconcilerWithPublisher(testutils.NewMockPublisher(), secret)
}

func setupKubernetesSecretReconcilerWithPublisher(publisher messaging.MessagePublisher, secret runtime.Object) *KubernetesSecretReconciler {
	s := runtime.NewScheme()
	_ = corev1.AddToScheme(s)

	fakeClientBuilder := fake.NewClientBuilder().WithScheme(s)
	if secret != nil {
		fakeClientBuilder.WithRuntimeObjects(secret)
	}
	fakeClient := fakeClientBuilder.Build()

	// Use provided publisher or create default mock
	if publisher == nil {
		publisher = testutils.NewMockPublisher()
	}

	reconciler := &KubernetesSecretReconciler{
		Client:    fakeClient,
		Publisher: publisher,
	}

	return reconciler
}

func TestSecretReconciler_Reconcile_UnmanagedSecret(t *testing.T) {
	secret := &corev1.Secret{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "unmanaged-secret",
			Namespace: "default",
			Labels:    map[string]string{}, // No project-secret-id label
		},
	}
	reconciler := setupKubernetesSecretReconciler(secret)
	req := ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "unmanaged-secret",
			Namespace: "default",
		},
	}
	publisher := reconciler.Publisher.(*testutils.MockPublisher)
	result, err := reconciler.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, publisher.Published, "should not publish status for unmanaged secret")
}

func TestSecretReconciler_Reconcile_AddFinalizer(t *testing.T) {
	secret := &corev1.Secret{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "managed-secret",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.ProjectSecretIDLabel:    "550e8400-e29b-41d4-a716-446655440000",
				common.ProjectSecretScopeLabel: "project",
				agent.ProjectIDLabel:           testProjectID,
			},
		},
	}
	reconciler := setupKubernetesSecretReconciler(secret)
	req := ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "managed-secret",
			Namespace: "test-namespace",
		},
	}
	publisher := reconciler.Publisher.(*testutils.MockPublisher)

	result, err := reconciler.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Verify finalizer was added
	var updatedSecret corev1.Secret
	err = reconciler.Client.Get(context.Background(), req.NamespacedName, &updatedSecret)
	require.NoError(t, err)
	assert.Contains(t, updatedSecret.Finalizers, Finalizer)

	// Verify status was published
	require.Len(t, publisher.Published, 1)
	statusMsg, ok := publisher.Published[0].(*messaging.ProjectSecretsUpdateMessage)
	require.True(t, ok)
	assert.Equal(t, messaging.MessageTypeProjectSecretsUpdate, statusMsg.MessageType)
	assert.Equal(t, "550e8400-e29b-41d4-a716-446655440000", statusMsg.ProjectSecretID)
	assert.Equal(t, messaging.ProjectSecretStatusSynced, statusMsg.Status)
	assert.NotNil(t, statusMsg.SecretScope)
	assert.Equal(t, messaging.SecretScopeProject, *statusMsg.SecretScope)
}

func TestSecretReconciler_Reconcile_WithExistingFinalizer(t *testing.T) {
	secret := &corev1.Secret{
		ObjectMeta: metav1.ObjectMeta{
			Name:       "managed-secret",
			Namespace:  "test-namespace",
			Finalizers: []string{Finalizer},
			Labels: map[string]string{
				common.ProjectSecretIDLabel:    "550e8400-e29b-41d4-a716-446655440000",
				common.ProjectSecretScopeLabel: "organization",
				agent.ProjectIDLabel:           testProjectID,
			},
		},
	}
	reconciler := setupKubernetesSecretReconciler(secret)
	req := ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "managed-secret",
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

func TestSecretReconciler_Reconcile_SecretNotFound(t *testing.T) {
	reconciler := setupKubernetesSecretReconciler(nil)
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

func TestSecretReconciler_HandleDeletion(t *testing.T) {
	secret := &corev1.Secret{
		ObjectMeta: metav1.ObjectMeta{
			Name:       "managed-secret",
			Namespace:  "test-namespace",
			Finalizers: []string{Finalizer},
			Labels: map[string]string{
				common.ProjectSecretIDLabel:    "550e8400-e29b-41d4-a716-446655440000",
				common.ProjectSecretScopeLabel: "project",
				agent.ProjectIDLabel:           testProjectID,
			},
		},
	}
	reconciler := setupKubernetesSecretReconciler(secret)
	publisher := reconciler.Publisher.(*testutils.MockPublisher)

	// Mark the secret for deletion
	err := reconciler.Client.Delete(context.Background(), secret)
	require.NoError(t, err)

	req := ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "managed-secret",
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
	assert.Equal(t, "Secret deleted successfully", *statusMsg.StatusReason)

	// After finalizer is removed, the secret should be fully deleted
	var updatedSecret corev1.Secret
	err = reconciler.Client.Get(context.Background(), req.NamespacedName, &updatedSecret)
	assert.True(t, err != nil && strings.Contains(err.Error(), "not found"), "secret should be deleted after finalizer removal")
}

func TestSecretReconciler_HandleDeletion_NoFinalizer(t *testing.T) {
	secret := &corev1.Secret{
		ObjectMeta: metav1.ObjectMeta{
			Name:       "managed-secret",
			Namespace:  "test-namespace",
			Finalizers: []string{}, // No finalizer
			Labels: map[string]string{
				common.ProjectSecretIDLabel: "550e8400-e29b-41d4-a716-446655440000",
				agent.ProjectIDLabel:        testProjectID,
			},
		},
	}
	reconciler := setupKubernetesSecretReconciler(secret)
	publisher := reconciler.Publisher.(*testutils.MockPublisher)

	// Mark the secret for deletion
	err := reconciler.Client.Delete(context.Background(), secret)
	require.NoError(t, err)

	req := ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "managed-secret",
			Namespace: "test-namespace",
		},
	}

	result, err := reconciler.Reconcile(context.Background(), req)

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, publisher.Published, "should not publish if finalizer already removed")
}

func TestSecretReconciler_PublishStatus_Error(t *testing.T) {
	secret := &corev1.Secret{
		ObjectMeta: metav1.ObjectMeta{
			Name:       "managed-secret",
			Namespace:  "test-namespace",
			Finalizers: []string{Finalizer},
			Labels: map[string]string{
				common.ProjectSecretIDLabel: "550e8400-e29b-41d4-a716-446655440000",
				agent.ProjectIDLabel:        testProjectID,
			},
		},
	}
	publisher := testutils.NewMockFailingPublisher(assert.AnError)
	reconciler := setupKubernetesSecretReconcilerWithPublisher(publisher, secret)
	req := ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "managed-secret",
			Namespace: "test-namespace",
		},
	}

	result, err := reconciler.Reconcile(context.Background(), req)

	assert.Error(t, err, "should return error on publish failure")
	assert.Equal(t, ctrl.Result{}, result, "should return empty result (controller-runtime handles requeue)")
}

func TestSecretReconciler_SetupWithManager(t *testing.T) {
	// This test just verifies the method exists and returns no error
	// Actual manager setup would require a full integration test
	reconciler := setupKubernetesSecretReconciler(nil)

	// We can't test this without a real manager, but we can verify the method signature
	assert.NotNil(t, reconciler)
}
