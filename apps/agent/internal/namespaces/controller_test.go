// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package namespaces

import (
	"context"
	"errors"
	"testing"

	agent "github.com/silogen/agent/internal/common"
	"github.com/silogen/agent/internal/testutils"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	corev1 "k8s.io/api/core/v1"
	rbacv1 "k8s.io/api/rbac/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"

	"github.com/silogen/agent/internal/messaging"
)

func setupReconciler(objects ...client.Object) (*NamespaceReconciler, client.Client) {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)
	_ = rbacv1.AddToScheme(scheme)

	fakeClient := fake.NewClientBuilder().
		WithScheme(scheme).
		WithObjects(objects...).
		Build()

	reconciler := &NamespaceReconciler{
		Client:    fakeClient,
		Publisher: testutils.NewMockPublisher(),
	}

	return reconciler, fakeClient
}

func TestReconcile_ManagedNamespace_AddsFinalizer(t *testing.T) {
	ns := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name: "test-namespace",
			Labels: map[string]string{
				agent.ProjectIDLabel: "project-123",
			},
		},
		Status: corev1.NamespaceStatus{
			Phase: corev1.NamespaceActive,
		},
	}

	reconciler, fakeClient := setupReconciler(ns)
	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{Name: "test-namespace"},
	})

	require.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Check finalizer was added
	var updatedNs corev1.Namespace
	err = fakeClient.Get(ctx, types.NamespacedName{Name: "test-namespace"}, &updatedNs)
	require.NoError(t, err)
	assert.Contains(t, updatedNs.Finalizers, namespaceFinalizer)

	// Check status was published
	mockPub := reconciler.Publisher.(*testutils.MockPublisher)
	require.Len(t, mockPub.Published, 1)
	msg, ok := mockPub.Published[0].(*messaging.ProjectNamespaceStatusMessage)
	require.True(t, ok)
	assert.Equal(t, "project-123", msg.ProjectID)
	assert.Equal(t, messaging.NamespaceStatusActive, msg.Status)
}

func TestReconcile_UnmanagedNamespace_AddsFinalizer(t *testing.T) {
	ns := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name: "test-namespace",
		},
		Status: corev1.NamespaceStatus{
			Phase: corev1.NamespaceActive,
		},
	}

	reconciler, fakeClient := setupReconciler(ns)
	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{Name: "test-namespace"},
	})

	require.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Check finalizer was added
	var updatedNs corev1.Namespace
	err = fakeClient.Get(ctx, types.NamespacedName{Name: "test-namespace"}, &updatedNs)
	require.NoError(t, err)
	assert.Contains(t, updatedNs.Finalizers, namespaceFinalizer)

	// Check unmanaged status was published
	mockPub := reconciler.Publisher.(*testutils.MockPublisher)
	require.Len(t, mockPub.Published, 1)
	msg, ok := mockPub.Published[0].(*messaging.UnmanagedNamespaceMessage)
	require.True(t, ok)
	assert.Equal(t, "test-namespace", msg.NamespaceName)
	assert.Equal(t, messaging.NamespaceStatusActive, msg.NamespaceStatus)
}

func TestReconcile_ManagedNamespace_CreatesRoleBinding(t *testing.T) {
	ns := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name: "test-namespace",
			UID:  types.UID("test-uid"),
			Labels: map[string]string{
				agent.ProjectIDLabel: "project-123",
			},
		},
		Status: corev1.NamespaceStatus{
			Phase: corev1.NamespaceActive,
		},
	}

	reconciler, fakeClient := setupReconciler(ns)
	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{Name: "test-namespace"},
	})

	require.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Check RoleBinding was created
	var rb rbacv1.RoleBinding
	err = fakeClient.Get(ctx, types.NamespacedName{
		Namespace: "test-namespace",
		Name:      "project-member-role-binding",
	}, &rb)
	require.NoError(t, err)
	assert.Equal(t, "test-namespace", rb.Namespace)
	assert.Equal(t, "airm-project-member", rb.RoleRef.Name)
	require.Len(t, rb.Subjects, 2)
	assert.Equal(t, "oidctest-namespace", rb.Subjects[0].Name)
	assert.Equal(t, "oidc:test-namespace", rb.Subjects[1].Name)

	// Check owner reference
	require.Len(t, rb.OwnerReferences, 1)
	assert.Equal(t, "test-namespace", rb.OwnerReferences[0].Name)
	assert.Equal(t, "Namespace", rb.OwnerReferences[0].Kind)
}

func TestReconcile_RoleBindingAlreadyExists(t *testing.T) {
	ns := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name: "test-namespace",
			UID:  types.UID("test-uid"),
			Labels: map[string]string{
				agent.ProjectIDLabel: "project-123",
			},
		},
		Status: corev1.NamespaceStatus{
			Phase: corev1.NamespaceActive,
		},
	}

	existingRB := &rbacv1.RoleBinding{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "project-member-role-binding",
			Namespace: "test-namespace",
		},
		RoleRef: rbacv1.RoleRef{
			APIGroup: "rbac.authorization.k8s.io",
			Kind:     "ClusterRole",
			Name:     "existing-role",
		},
	}

	reconciler, fakeClient := setupReconciler(ns, existingRB)
	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{Name: "test-namespace"},
	})

	require.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Check RoleBinding was NOT recreated
	var rb rbacv1.RoleBinding
	err = fakeClient.Get(ctx, types.NamespacedName{
		Namespace: "test-namespace",
		Name:      "project-member-role-binding",
	}, &rb)
	require.NoError(t, err)
	assert.Equal(t, "existing-role", rb.RoleRef.Name) // Still has original role
}

func TestReconcile_NamespaceWithExistingFinalizer(t *testing.T) {
	ns := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name:       "test-namespace",
			Finalizers: []string{namespaceFinalizer},
			Labels: map[string]string{
				agent.ProjectIDLabel: "project-123",
			},
		},
		Status: corev1.NamespaceStatus{
			Phase: corev1.NamespaceActive,
		},
	}

	reconciler, _ := setupReconciler(ns)
	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{Name: "test-namespace"},
	})

	require.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Should still publish status
	mockPub := reconciler.Publisher.(*testutils.MockPublisher)
	require.Len(t, mockPub.Published, 1)
}

func TestReconcile_NamespaceBeingDeleted_RemovesFinalizer(t *testing.T) {
	now := metav1.Now()
	ns := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-namespace",
			Finalizers:        []string{namespaceFinalizer},
			DeletionTimestamp: &now,
			Labels: map[string]string{
				agent.ProjectIDLabel: "project-123",
			},
		},
		Status: corev1.NamespaceStatus{
			Phase: corev1.NamespaceActive,
		},
	}

	reconciler, _ := setupReconciler(ns)
	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{Name: "test-namespace"},
	})

	require.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	mockPub := reconciler.Publisher.(*testutils.MockPublisher)
	require.Len(t, mockPub.Published, 1)
	statusMsg, ok := mockPub.Published[0].(*messaging.ProjectNamespaceStatusMessage)
	require.True(t, ok)
	assert.Equal(t, messaging.NamespaceStatusTerminating, statusMsg.Status)
}

func TestReconcile_NamespaceDeleted(t *testing.T) {
	reconciler, _ := setupReconciler()
	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{Name: "test-namespace"},
	})

	require.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	mockPub := reconciler.Publisher.(*testutils.MockPublisher)
	require.Len(t, mockPub.Published, 1)

	msg, ok := mockPub.Published[0].(*messaging.NamespaceDeletedMessage)
	require.True(t, ok)
	assert.Equal(t, msg.NamespaceName, "test-namespace")
}

func TestReconcile_UnmanagedNamespaceBeingDeleted(t *testing.T) {
	now := metav1.Now()
	ns := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-namespace",
			Finalizers:        []string{namespaceFinalizer},
			DeletionTimestamp: &now,
		},
		Status: corev1.NamespaceStatus{
			Phase: corev1.NamespaceActive,
		},
	}

	reconciler, _ := setupReconciler(ns)
	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{Name: "test-namespace"},
	})

	require.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Check unmanaged deletion status was published
	mockPub := reconciler.Publisher.(*testutils.MockPublisher)
	require.Len(t, mockPub.Published, 1)
	msg, ok := mockPub.Published[0].(*messaging.UnmanagedNamespaceMessage)
	require.True(t, ok)
	assert.Equal(t, messaging.NamespaceStatusTerminating, msg.NamespaceStatus)
}

func TestReconcile_NamespaceBeingDeleted_WithoutFinalizer(t *testing.T) {
	// Note: Fake client won't allow creating namespace with deletionTimestamp and no finalizers
	// So we test by creating it with finalizer, then calling reconcile
	now := metav1.Now()
	ns := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-namespace",
			Finalizers:        []string{"some-other-finalizer"}, // Different finalizer
			DeletionTimestamp: &now,
			Labels: map[string]string{
				agent.ProjectIDLabel: "project-123",
			},
		},
	}

	reconciler, _ := setupReconciler(ns)
	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{Name: "test-namespace"},
	})

	require.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Should not publish (our finalizer not present)
	mockPub := reconciler.Publisher.(*testutils.MockPublisher)
	assert.Len(t, mockPub.Published, 0)
}

func TestReconcile_PublishError_RequeuesForStatus(t *testing.T) {
	ns := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name: "test-namespace",
			Labels: map[string]string{
				agent.ProjectIDLabel: "project-123",
			},
		},
		Status: corev1.NamespaceStatus{
			Phase: corev1.NamespaceActive,
		},
	}

	reconciler, _ := setupReconciler(ns)
	mockPub := reconciler.Publisher.(*testutils.MockPublisher)
	mockPub.PublishError = errors.New("publish failed")

	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{Name: "test-namespace"},
	})

	require.Error(t, err)
	assert.Equal(t, ctrl.Result{}, result)
}

func TestReconcile_PublishError_RequeuesForDeletion(t *testing.T) {
	now := metav1.Now()
	ns := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-namespace",
			Finalizers:        []string{namespaceFinalizer},
			DeletionTimestamp: &now,
			Labels: map[string]string{
				agent.ProjectIDLabel: "project-123",
			},
		},
	}

	reconciler, _ := setupReconciler(ns)
	mockPub := reconciler.Publisher.(*testutils.MockPublisher)
	mockPub.PublishError = errors.New("publish failed")

	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{Name: "test-namespace"},
	})

	require.Error(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Verify publish was attempted
	assert.Len(t, mockPub.Published, 0) // No messages due to error
}

func TestReconcile_DifferentPhases(t *testing.T) {
	tests := []struct {
		name           string
		phase          corev1.NamespacePhase
		expectedStatus messaging.NamespaceStatus
	}{
		{
			name:           "Active phase",
			phase:          corev1.NamespaceActive,
			expectedStatus: messaging.NamespaceStatusActive,
		},
		{
			name:           "Terminating phase",
			phase:          corev1.NamespaceTerminating,
			expectedStatus: messaging.NamespaceStatusTerminating,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			ns := &corev1.Namespace{
				ObjectMeta: metav1.ObjectMeta{
					Name: "test-namespace",
					Labels: map[string]string{
						agent.ProjectIDLabel: "project-123",
					},
				},
				Status: corev1.NamespaceStatus{
					Phase: tt.phase,
				},
			}

			reconciler, _ := setupReconciler(ns)
			ctx := ctrl.LoggerInto(context.Background(), zap.New())

			result, err := reconciler.Reconcile(ctx, ctrl.Request{
				NamespacedName: types.NamespacedName{Name: "test-namespace"},
			})

			require.NoError(t, err)
			assert.Equal(t, ctrl.Result{}, result)

			mockPub := reconciler.Publisher.(*testutils.MockPublisher)
			require.Len(t, mockPub.Published, 1)
			msg, ok := mockPub.Published[0].(*messaging.ProjectNamespaceStatusMessage)
			require.True(t, ok)
			assert.Equal(t, tt.expectedStatus, msg.Status)
		})
	}
}
