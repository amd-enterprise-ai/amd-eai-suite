// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package configmap

import (
	"context"
	"errors"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"

	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/testutils"
)

func setupConfigMapReconciler(objects ...client.Object) (*ConfigMapReconciler, client.Client, *testutils.MockPublisher) {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)

	fakeClient := fake.NewClientBuilder().
		WithScheme(scheme).
		WithObjects(objects...).
		Build()

	mockPub := testutils.NewMockPublisher()
	reconciler := &ConfigMapReconciler{
		Client:    fakeClient,
		Publisher: mockPub,
	}

	return reconciler, fakeClient, mockPub
}

func TestConfigMapReconcile_ManagedConfigMap_AddsFinalizer(t *testing.T) {
	cm := &corev1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-configmap",
			Namespace: "test-namespace",
			Labels: map[string]string{
				ProjectStorageIDLabel: "storage-123",
			},
		},
	}

	reconciler, fakeClient, mockPub := setupConfigMapReconciler(cm)
	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "test-configmap",
			Namespace: "test-namespace",
		},
	})

	require.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Check finalizer was added
	var updatedCM corev1.ConfigMap
	err = fakeClient.Get(ctx, types.NamespacedName{
		Name:      "test-configmap",
		Namespace: "test-namespace",
	}, &updatedCM)
	require.NoError(t, err)
	assert.Contains(t, updatedCM.Finalizers, ConfigMapFinalizer)

	// Status published in the same reconcile
	require.Len(t, mockPub.Published, 1)
	msg, ok := mockPub.Published[0].(*messaging.ProjectStorageUpdateMessage)
	require.True(t, ok)
	assert.Equal(t, "storage-123", msg.ProjectStorageID)
	assert.Equal(t, messaging.ConfigMapStatusAdded, msg.Status)
}

func TestConfigMapReconcile_UnmanagedConfigMap_Ignored(t *testing.T) {
	cm := &corev1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-configmap",
			Namespace: "test-namespace",
			// No ProjectStorageIDLabel
		},
	}

	reconciler, fakeClient, mockPub := setupConfigMapReconciler(cm)
	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "test-configmap",
			Namespace: "test-namespace",
		},
	})

	require.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Check NO finalizer was added (unmanaged)
	var updatedCM corev1.ConfigMap
	err = fakeClient.Get(ctx, types.NamespacedName{
		Name:      "test-configmap",
		Namespace: "test-namespace",
	}, &updatedCM)
	require.NoError(t, err)
	assert.NotContains(t, updatedCM.Finalizers, ConfigMapFinalizer)

	// Check NO status was published
	assert.Len(t, mockPub.Published, 0)
}

func TestConfigMapReconcile_ConfigMapWithExistingFinalizer(t *testing.T) {
	cm := &corev1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name:       "test-configmap",
			Namespace:  "test-namespace",
			Finalizers: []string{ConfigMapFinalizer},
			Labels: map[string]string{
				ProjectStorageIDLabel: "storage-123",
			},
		},
	}

	reconciler, _, mockPub := setupConfigMapReconciler(cm)
	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "test-configmap",
			Namespace: "test-namespace",
		},
	})

	require.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Should publish status
	require.Len(t, mockPub.Published, 1)
}

func TestConfigMapReconcile_ConfigMapBeingDeleted_RemovesFinalizer(t *testing.T) {
	now := metav1.Now()
	cm := &corev1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-configmap",
			Namespace:         "test-namespace",
			Finalizers:        []string{ConfigMapFinalizer},
			DeletionTimestamp: &now,
			Labels: map[string]string{
				ProjectStorageIDLabel: "storage-123",
			},
		},
	}

	reconciler, _, mockPub := setupConfigMapReconciler(cm)
	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "test-configmap",
			Namespace: "test-namespace",
		},
	})

	require.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Check deletion status was published
	require.Len(t, mockPub.Published, 1)
	msg, ok := mockPub.Published[0].(*messaging.ProjectStorageUpdateMessage)
	require.True(t, ok)
	assert.Equal(t, messaging.ConfigMapStatusDeleted, msg.Status)
}

func TestConfigMapReconcile_ConfigMapBeingDeleted_WithoutFinalizer(t *testing.T) {
	now := metav1.Now()
	cm := &corev1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-configmap",
			Namespace:         "test-namespace",
			Finalizers:        []string{"some-other-finalizer"},
			DeletionTimestamp: &now,
			Labels: map[string]string{
				ProjectStorageIDLabel: "storage-123",
			},
		},
	}

	reconciler, _, mockPub := setupConfigMapReconciler(cm)
	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "test-configmap",
			Namespace: "test-namespace",
		},
	})

	require.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Should not publish (our finalizer not present)
	assert.Len(t, mockPub.Published, 0)
}

func TestConfigMapReconcile_ConfigMapNotFound(t *testing.T) {
	reconciler, _, mockPub := setupConfigMapReconciler()
	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "non-existent",
			Namespace: "test-namespace",
		},
	})

	require.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	// Should not publish anything
	assert.Len(t, mockPub.Published, 0)
}

func TestConfigMapReconcile_PublishError_RequeuesForStatus(t *testing.T) {
	cm := &corev1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name:       "test-configmap",
			Namespace:  "test-namespace",
			Finalizers: []string{ConfigMapFinalizer},
			Labels: map[string]string{
				ProjectStorageIDLabel: "storage-123",
			},
		},
	}

	reconciler, _, mockPub := setupConfigMapReconciler(cm)
	mockPub.PublishError = errors.New("publish failed")

	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "test-configmap",
			Namespace: "test-namespace",
		},
	})

	require.Error(t, err)
	assert.Equal(t, ctrl.Result{}, result, "should return empty result with error")
}

func TestConfigMapReconcile_PublishError_RequeuesForDeletion(t *testing.T) {
	now := metav1.Now()
	cm := &corev1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-configmap",
			Namespace:         "test-namespace",
			Finalizers:        []string{ConfigMapFinalizer},
			DeletionTimestamp: &now,
			Labels: map[string]string{
				ProjectStorageIDLabel: "storage-123",
			},
		},
	}

	reconciler, _, mockPub := setupConfigMapReconciler(cm)
	mockPub.PublishError = errors.New("publish failed")

	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{
			Name:      "test-configmap",
			Namespace: "test-namespace",
		},
	})

	require.Error(t, err)
	assert.Equal(t, ctrl.Result{}, result, "should return empty result with error")
}
