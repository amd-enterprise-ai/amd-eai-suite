// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package service

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

	svc := &corev1.Service{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-service",
			Namespace: "test-namespace",
			Labels: map[string]string{
				common.WorkloadIDLabel:  uuid.New().String(),
				common.ComponentIDLabel: uuid.New().String(),
				agent.ProjectIDLabel:    uuid.New().String(),
			},
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(svc).Build()
	r := &Reconciler{Client: c, Publisher: testutils.NewMockPublisher()}

	result, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: svc.Name, Namespace: svc.Namespace},
	})

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	var updated corev1.Service
	_ = c.Get(context.Background(), types.NamespacedName{Name: svc.Name, Namespace: svc.Namespace}, &updated)
	assert.True(t, controllerutil.ContainsFinalizer(&updated, common.WorkloadFinalizer))
}

func TestReconcile_HandlesDeletion(t *testing.T) {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)

	workloadID := uuid.New()
	componentID := uuid.New()
	now := metav1.Now()

	svc := &corev1.Service{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-service",
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

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(svc).Build()
	mock := testutils.NewMockPublisher()
	r := &Reconciler{Client: c, Publisher: mock}

	result, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: svc.Name, Namespace: svc.Namespace},
	})

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Len(t, mock.Published, 1)

	msg, ok := mock.Published[0].(messaging.WorkloadComponentStatusMessage)
	assert.True(t, ok)
	assert.Equal(t, "test-service", msg.Name)
	assert.Equal(t, "Deleted", msg.Status)
	assert.Equal(t, workloadID.String(), msg.WorkloadID)
}

func TestReconcile_IgnoresServiceWithoutWorkloadLabel(t *testing.T) {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)

	svc := &corev1.Service{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "kubernetes",
			Namespace: "default",
			// No workload-id label
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(svc).Build()
	mock := testutils.NewMockPublisher()
	r := &Reconciler{Client: c, Publisher: mock}

	result, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: svc.Name, Namespace: svc.Namespace},
	})

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Empty(t, mock.Published)

	var updated corev1.Service
	_ = c.Get(context.Background(), types.NamespacedName{Name: svc.Name, Namespace: svc.Namespace}, &updated)
	assert.False(t, controllerutil.ContainsFinalizer(&updated, common.WorkloadFinalizer))
}
