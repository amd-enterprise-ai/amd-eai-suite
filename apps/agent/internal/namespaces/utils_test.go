// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package namespaces

import (
	"context"
	"testing"

	agent "github.com/silogen/agent/internal/common"
	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/testutils"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
)

func newTestScheme() *runtime.Scheme {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)
	return scheme
}

func TestExtractProjectIDFromNamespace(t *testing.T) {
	tests := []struct {
		name string
		ns   *corev1.Namespace
		want string
	}{
		{
			name: "has project id label",
			ns: &corev1.Namespace{
				ObjectMeta: metav1.ObjectMeta{
					Name: "test-ns",
					Labels: map[string]string{
						agent.ProjectIDLabel: "project-123",
					},
				},
			},
			want: "project-123",
		},
		{
			name: "empty labels",
			ns: &corev1.Namespace{
				ObjectMeta: metav1.ObjectMeta{Name: "test-ns", Labels: map[string]string{}},
			},
			want: "",
		},
		{
			name: "nil labels",
			ns: &corev1.Namespace{
				ObjectMeta: metav1.ObjectMeta{Name: "test-ns"},
			},
			want: "",
		},
		{
			name: "nil namespace",
			ns:   nil,
			want: "",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := extractProjectIDFromNamespace(tt.ns)
			assert.Equal(t, tt.want, got)
		})
	}
}

func TestMapK8sPhaseToNamespaceStatus(t *testing.T) {
	tests := []struct {
		name  string
		phase string
		want  messaging.NamespaceStatus
	}{
		{
			name:  "Active phase",
			phase: "Active",
			want:  messaging.NamespaceStatusActive,
		},
		{
			name:  "Terminating phase",
			phase: "Terminating",
			want:  messaging.NamespaceStatusTerminating,
		},
		{
			name:  "Pending phase",
			phase: "Pending",
			want:  messaging.NamespaceStatusPending,
		},
		{
			name:  "Unknown phase",
			phase: "Unknown",
			want:  messaging.NamespaceStatusFailed,
		},
		{
			name:  "Empty phase",
			phase: "",
			want:  messaging.NamespaceStatusFailed,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := mapK8sPhaseToNamespaceStatus(tt.phase)
			assert.Equal(t, tt.want, got)
		})
	}
}

func TestGetNamespaceStatusReason_FromHandlers(t *testing.T) {
	tests := []struct {
		name   string
		status messaging.NamespaceStatus
		want   string
	}{
		{
			name:   "Deleted status",
			status: messaging.NamespaceStatusDeleted,
			want:   "Namespace has been deleted",
		},
		{
			name:   "Active status",
			status: messaging.NamespaceStatusActive,
			want:   "Namespace is active",
		},
		{
			name:   "Terminating status",
			status: messaging.NamespaceStatusTerminating,
			want:   "Namespace is terminating",
		},
		{
			name:   "Pending status",
			status: messaging.NamespaceStatusPending,
			want:   "Namespace is pending",
		},
		{
			name:   "DeleteFailed status",
			status: messaging.NamespaceStatusDeleteFailed,
			want:   "Namespace deletion failed",
		},
		{
			name:   "Failed status",
			status: messaging.NamespaceStatusFailed,
			want:   "Unknown namespace phase: Unknown",
		},
		{
			name:   "Unknown status",
			status: messaging.NamespaceStatus("Unknown"),
			want:   "Unknown namespace status",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := GetNamespaceStatusReason(tt.status)
			assert.Equal(t, tt.want, got)
		})
	}
}

func TestHandleDeletion_NoFinalizer(t *testing.T) {
	scheme := newTestScheme()
	now := metav1.Now()
	ns := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-ns",
			DeletionTimestamp: &now,
			Finalizers:        []string{"some-other-finalizer"},
			Labels: map[string]string{
				agent.ProjectIDLabel: "project-123",
			},
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(ns).Build()
	pub := testutils.NewMockPublisher()

	err := HandleDeletion(context.Background(), c, pub, ns)

	assert.NoError(t, err)
	assert.Empty(t, pub.Published)
}

func TestHandleDeletion_ManagedNamespace_PublishesAndRemovesFinalizer(t *testing.T) {
	scheme := newTestScheme()
	now := metav1.Now()
	ns := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-ns",
			DeletionTimestamp: &now,
			Finalizers:        []string{namespaceFinalizer},
			Labels: map[string]string{
				agent.ProjectIDLabel: "project-123",
			},
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(ns).Build()
	pub := testutils.NewMockPublisher()

	err := HandleDeletion(context.Background(), c, pub, ns)

	assert.NoError(t, err)

	require.Len(t, pub.Published, 1)
	msg, ok := pub.Published[0].(*messaging.ProjectNamespaceStatusMessage)
	require.True(t, ok)
	assert.Equal(t, "project-123", msg.ProjectID)
	assert.Equal(t, messaging.NamespaceStatusTerminating, msg.Status)
	require.NotNil(t, msg.StatusReason)
	assert.Equal(t, "Namespace is terminating", *msg.StatusReason)

	assert.False(t, controllerutil.ContainsFinalizer(ns, namespaceFinalizer))
}

func TestHandleDeletion_UnmanagedNamespace_PublishesAndRemovesFinalizer(t *testing.T) {
	scheme := newTestScheme()
	now := metav1.Now()
	ns := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-ns",
			DeletionTimestamp: &now,
			Finalizers:        []string{namespaceFinalizer},
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(ns).Build()
	pub := testutils.NewMockPublisher()

	err := HandleDeletion(context.Background(), c, pub, ns)

	assert.NoError(t, err)

	require.Len(t, pub.Published, 1)
	msg, ok := pub.Published[0].(*messaging.UnmanagedNamespaceMessage)
	require.True(t, ok)
	assert.Equal(t, "test-ns", msg.NamespaceName)
	assert.Equal(t, messaging.NamespaceStatusTerminating, msg.NamespaceStatus)

	assert.False(t, controllerutil.ContainsFinalizer(ns, namespaceFinalizer))
}

func TestHandleDeletion_PublishFails_RetainsFinalizer(t *testing.T) {
	scheme := newTestScheme()
	now := metav1.Now()
	ns := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-ns",
			DeletionTimestamp: &now,
			Finalizers:        []string{namespaceFinalizer},
			Labels: map[string]string{
				agent.ProjectIDLabel: "project-123",
			},
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(ns).Build()
	pub := testutils.NewMockFailingPublisher(assert.AnError)

	err := HandleDeletion(context.Background(), c, pub, ns)

	assert.ErrorIs(t, err, assert.AnError)
	assert.Empty(t, pub.Published)
	assert.True(t, controllerutil.ContainsFinalizer(ns, namespaceFinalizer))
}
