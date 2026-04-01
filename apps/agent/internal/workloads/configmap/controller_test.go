// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package configmap

import (
	"context"
	"testing"

	"github.com/google/uuid"
	agent "github.com/silogen/agent/internal/common"
	"github.com/stretchr/testify/assert"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	"sigs.k8s.io/controller-runtime/pkg/reconcile"

	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/testutils"
	"github.com/silogen/agent/internal/workloads/common"
)

func TestReconcile_AddsFinalizer(t *testing.T) {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)

	cm := &corev1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-configmap",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  uuid.New().String(),
				common.ComponentIDLabel: uuid.New().String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(cm).Build()
	r := &Reconciler{Client: c, Publisher: testutils.NewMockPublisher()}

	result, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: cm.Name, Namespace: cm.Namespace},
	})

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	var updated corev1.ConfigMap
	_ = c.Get(context.Background(), types.NamespacedName{Name: cm.Name, Namespace: cm.Namespace}, &updated)
	assert.True(t, controllerutil.ContainsFinalizer(&updated, common.WorkloadFinalizer))
}

func TestReconcile_HandlesDeletion(t *testing.T) {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)

	workloadID := uuid.New()
	componentID := uuid.New()
	now := metav1.Now()

	cm := &corev1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-configmap",
			Namespace:         "test-namespace",
			DeletionTimestamp: &now,
			Finalizers:        []string{common.WorkloadFinalizer},
			Labels: map[string]string{
				common.WorkloadIDLabel:  workloadID.String(),
				common.ComponentIDLabel: componentID.String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(cm).Build()
	mock := testutils.NewMockPublisher()
	r := &Reconciler{Client: c, Publisher: mock}

	result, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: cm.Name, Namespace: cm.Namespace},
	})

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Len(t, mock.Published, 1)

	msg, ok := mock.Published[0].(messaging.WorkloadComponentStatusMessage)
	assert.True(t, ok)
	assert.Equal(t, "test-configmap", msg.Name)
	assert.Equal(t, "Deleted", msg.Status)
	assert.Equal(t, workloadID.String(), msg.WorkloadID)
}

func TestReconcile_IgnoresConfigMapWithoutWorkloadLabel(t *testing.T) {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)

	// ConfigMap without workload-id label (e.g., storage ConfigMap or other ConfigMap)
	cm := &corev1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "storage-configmap",
			Namespace: "test-namespace",
			Labels: map[string]string{
				"airm.silogen.ai/project-storage-id": uuid.New().String(), // Storage label, not workload label
			},
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(cm).Build()
	mock := testutils.NewMockPublisher()
	r := &Reconciler{Client: c, Publisher: mock}

	result, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: cm.Name, Namespace: cm.Namespace},
	})

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, mock.Published) // Should not publish anything

	// Verify no finalizer was added
	var updated corev1.ConfigMap
	_ = c.Get(context.Background(), types.NamespacedName{Name: cm.Name, Namespace: cm.Namespace}, &updated)
	assert.False(t, controllerutil.ContainsFinalizer(&updated, common.WorkloadFinalizer))
}

func TestReconcile_IgnoresConfigMapWithNoLabels(t *testing.T) {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)

	cm := &corev1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "regular-configmap",
			Namespace: "test-namespace",
			// No labels at all
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(cm).Build()
	mock := testutils.NewMockPublisher()
	r := &Reconciler{Client: c, Publisher: mock}

	result, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: cm.Name, Namespace: cm.Namespace},
	})

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, mock.Published) // Should not publish anything
}

func TestSetupWithManager(t *testing.T) {
	// This is a basic test to ensure SetupWithManager doesn't panic
	// Full integration testing would require a real manager
	r := &Reconciler{}
	assert.NotNil(t, r)
}
