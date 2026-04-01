// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package nodes

import (
	"context"
	"testing"
	"time"

	"github.com/silogen/agent/internal/testutils"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	corev1 "k8s.io/api/core/v1"
	rbacv1 "k8s.io/api/rbac/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"

	"github.com/silogen/agent/internal/messaging"
)

func setupReconciler(node client.Object) *NodeReconciler {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)
	_ = rbacv1.AddToScheme(scheme)

	fakeClientBuilder := fake.NewClientBuilder()
	if node != nil {
		fakeClientBuilder.WithRuntimeObjects(node)
	}
	fakeClient := fakeClientBuilder.Build()

	reconciler := &NodeReconciler{
		Client:    fakeClient,
		Publisher: testutils.NewMockPublisher(),
	}

	return reconciler
}

func TestReconcile_NodeUpdate(t *testing.T) {
	node := &corev1.Node{
		ObjectMeta: metav1.ObjectMeta{
			Name: "test-node",
		},
		Status: corev1.NodeStatus{
			Allocatable: corev1.ResourceList{
				corev1.ResourceCPU:              resource.MustParse("1"),
				corev1.ResourceMemory:           resource.MustParse("1Gi"),
				corev1.ResourceEphemeralStorage: resource.MustParse("1Gi"),
			},
		},
	}

	reconciler := setupReconciler(node)
	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{Name: "test-node"},
	})

	require.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	mockPub := reconciler.Publisher.(*testutils.MockPublisher)
	require.Len(t, mockPub.Published, 1)
	msg, ok := mockPub.Published[0].(*messaging.ClusterNodeUpdateMessage)
	require.True(t, ok)
	assert.Equal(t, "test-node", msg.ClusterNode.Name)
}

func TestReconcile_NodePendingDeletion(t *testing.T) {
	node := &corev1.Node{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-node",
			DeletionTimestamp: &metav1.Time{Time: time.Now()},
			Finalizers:        []string{"finalizer"},
		},
		Status: corev1.NodeStatus{
			Allocatable: corev1.ResourceList{
				corev1.ResourceCPU:              resource.MustParse("1"),
				corev1.ResourceMemory:           resource.MustParse("1Gi"),
				corev1.ResourceEphemeralStorage: resource.MustParse("1Gi"),
			},
		},
	}

	reconciler := setupReconciler(node)
	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{Name: "test-node"},
	})

	require.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	mockPub := reconciler.Publisher.(*testutils.MockPublisher)
	require.Len(t, mockPub.Published, 1)
	msg, ok := mockPub.Published[0].(*messaging.ClusterNodeDeleteMessage)
	require.True(t, ok)
	assert.Equal(t, "test-node", msg.Name)
}

func TestReconcile_NodeDeleted(t *testing.T) {
	reconciler := setupReconciler(nil)
	ctx := ctrl.LoggerInto(context.Background(), zap.New())

	result, err := reconciler.Reconcile(ctx, ctrl.Request{
		NamespacedName: types.NamespacedName{Name: "test-node"},
	})

	require.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	mockPub := reconciler.Publisher.(*testutils.MockPublisher)
	require.Len(t, mockPub.Published, 1)
	msg, ok := mockPub.Published[0].(*messaging.ClusterNodeDeleteMessage)
	require.True(t, ok)
	assert.Equal(t, "test-node", msg.Name)
}
