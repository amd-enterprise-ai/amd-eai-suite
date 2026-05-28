// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package namespaces

import (
	"context"
	"testing"

	agent "github.com/silogen/agent/internal/common"
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
		want  NamespaceStatus
	}{
		{
			name:  "Active phase",
			phase: "Active",
			want:  NamespaceStatusActive,
		},
		{
			name:  "Terminating phase",
			phase: "Terminating",
			want:  NamespaceStatusTerminating,
		},
		{
			name:  "Pending phase",
			phase: "Pending",
			want:  NamespaceStatusPending,
		},
		{
			name:  "Unknown phase",
			phase: "Unknown",
			want:  NamespaceStatusFailed,
		},
		{
			name:  "Empty phase",
			phase: "",
			want:  NamespaceStatusFailed,
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
		status NamespaceStatus
		want   string
	}{
		{
			name:   "Deleted status",
			status: NamespaceStatusDeleted,
			want:   "Namespace has been deleted",
		},
		{
			name:   "Active status",
			status: NamespaceStatusActive,
			want:   "Namespace is active",
		},
		{
			name:   "Terminating status",
			status: NamespaceStatusTerminating,
			want:   "Namespace is terminating",
		},
		{
			name:   "Pending status",
			status: NamespaceStatusPending,
			want:   "Namespace is pending",
		},
		{
			name:   "DeleteFailed status",
			status: NamespaceStatusDeleteFailed,
			want:   "Namespace deletion failed",
		},
		{
			name:   "Failed status",
			status: NamespaceStatusFailed,
			want:   "Unknown namespace phase: Unknown",
		},
		{
			name:   "Unknown status",
			status: NamespaceStatus("Unknown"),
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
	msg, ok := pub.Published[0].(*ProjectNamespaceStatusMessage)
	require.True(t, ok)
	assert.Equal(t, "project-123", msg.ProjectID)
	assert.Equal(t, NamespaceStatusTerminating, msg.Status)
	require.NotNil(t, msg.StatusReason)
	assert.Equal(t, "Namespace is terminating", *msg.StatusReason)
	assert.Nil(t, msg.GpuPreemption, "gpu_preemption must be omitted for terminating status")

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
	msg, ok := pub.Published[0].(*UnmanagedNamespaceMessage)
	require.True(t, ok)
	assert.Equal(t, "test-ns", msg.NamespaceName)
	assert.Equal(t, NamespaceStatusTerminating, msg.NamespaceStatus)

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

func TestGpuPreemptionStatusFromNamespace_FullConfig(t *testing.T) {
	ns := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Annotations: map[string]string{
				KaiwoGpuPreemptionEnabledKey:     "true",
				KaiwoGpuPreemptionThresholdKey:   "80",
				KaiwoGpuPreemptionGracePeriodKey: "30m",
				KaiwoGpuPreemptionPolicyKey:      string(GpuPreemptionPolicyOnPressure),
			},
		},
	}

	got := gpuPreemptionStatusFromNamespace(context.Background(), ns)

	require.NotNil(t, got)
	assert.True(t, got.Enabled)
	require.NotNil(t, got.Threshold)
	assert.Equal(t, 80, *got.Threshold)
	require.NotNil(t, got.GracePeriod)
	assert.Equal(t, 1800, *got.GracePeriod)
	require.NotNil(t, got.Policy)
	assert.Equal(t, GpuPreemptionPolicyOnPressure, *got.Policy)
}

func TestGpuPreemptionStatusFromNamespace_NoAnnotations(t *testing.T) {
	ns := &corev1.Namespace{ObjectMeta: metav1.ObjectMeta{Name: "test-ns"}}

	got := gpuPreemptionStatusFromNamespace(context.Background(), ns)

	require.NotNil(t, got)
	assert.False(t, got.Enabled)
	assert.Nil(t, got.Threshold)
	assert.Nil(t, got.GracePeriod)
	assert.Nil(t, got.Policy)
}

func TestGpuPreemptionStatusFromNamespace_NilNamespace(t *testing.T) {
	got := gpuPreemptionStatusFromNamespace(context.Background(), nil)

	require.NotNil(t, got)
	assert.False(t, got.Enabled)
}

func TestGpuPreemptionStatusFromNamespace_DisabledExplicit(t *testing.T) {
	ns := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Annotations: map[string]string{
				KaiwoGpuPreemptionEnabledKey: "false",
			},
		},
	}

	got := gpuPreemptionStatusFromNamespace(context.Background(), ns)

	require.NotNil(t, got)
	assert.False(t, got.Enabled)
	assert.Nil(t, got.Threshold)
}

func TestGpuPreemptionStatusFromNamespace_InvalidAnnotations(t *testing.T) {
	ns := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name: "test-ns",
			Annotations: map[string]string{
				KaiwoGpuPreemptionEnabledKey:     "notabool",
				KaiwoGpuPreemptionThresholdKey:   "notanint",
				KaiwoGpuPreemptionGracePeriodKey: "notaduration",
			},
		},
	}

	got := gpuPreemptionStatusFromNamespace(context.Background(), ns)

	require.NotNil(t, got)
	assert.False(t, got.Enabled)
	assert.Nil(t, got.Threshold)
	assert.Nil(t, got.GracePeriod)
}

func TestGpuPreemptionStatusFromNamespace_ThresholdPassedThrough(t *testing.T) {
	ns := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name: "test-ns",
			Annotations: map[string]string{
				KaiwoGpuPreemptionThresholdKey: "101",
			},
		},
	}

	got := gpuPreemptionStatusFromNamespace(context.Background(), ns)

	require.NotNil(t, got.Threshold, "threshold value should be passed through regardless of range")
	assert.Equal(t, 101, *got.Threshold)
}

func TestGpuPreemptionStatusFromNamespace_InvalidPolicy(t *testing.T) {
	ns := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name: "test-ns",
			Annotations: map[string]string{
				KaiwoGpuPreemptionPolicyKey: "evict",
			},
		},
	}

	got := gpuPreemptionStatusFromNamespace(context.Background(), ns)

	assert.Nil(t, got.Policy, "unrecognized policy value must be omitted")
}

func TestGpuPreemptionStatusFromNamespace_GracePeriodPassedThrough(t *testing.T) {
	ns := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name: "test-ns",
			Annotations: map[string]string{
				KaiwoGpuPreemptionGracePeriodKey: "10m",
			},
		},
	}

	got := gpuPreemptionStatusFromNamespace(context.Background(), ns)

	require.NotNil(t, got.GracePeriod, "grace_period value should be passed through regardless of range")
	assert.Equal(t, 600, *got.GracePeriod)
}

func TestMergeKaiwoAnnotations_UpsertsAndStripsKaiwoKeys(t *testing.T) {
	existing := map[string]string{
		"other.app/key":                "keep",
		KaiwoGpuPreemptionEnabledKey:   "false",
		KaiwoGpuPreemptionThresholdKey: "80",
	}
	manifest := map[string]string{
		KaiwoGpuPreemptionEnabledKey: "true",
		// threshold absent → should be removed
	}

	got := mergeKaiwoAnnotations(existing, manifest)

	assert.Equal(t, "keep", got["other.app/key"], "non-Kaiwo key must be preserved")
	assert.Equal(t, "true", got[KaiwoGpuPreemptionEnabledKey], "present Kaiwo key must be upserted")
	_, hasThreshold := got[KaiwoGpuPreemptionThresholdKey]
	assert.False(t, hasThreshold, "absent Kaiwo key must be removed")
}

func TestMergeKaiwoAnnotations_PreservesNonKaiwoKeys(t *testing.T) {
	existing := map[string]string{"unrelated/key": "stay"}
	manifest := map[string]string{}

	got := mergeKaiwoAnnotations(existing, manifest)
	assert.Equal(t, "stay", got["unrelated/key"])
}

func TestMergeKaiwoAnnotations_NilExisting(t *testing.T) {
	manifest := map[string]string{KaiwoGpuPreemptionEnabledKey: "true"}
	got := mergeKaiwoAnnotations(nil, manifest)
	assert.Equal(t, "true", got[KaiwoGpuPreemptionEnabledKey])
}

func TestMergeKaiwoAnnotations_NilManifest(t *testing.T) {
	existing := map[string]string{
		"other/key":                  "keep",
		KaiwoGpuPreemptionEnabledKey: "true",
	}
	got := mergeKaiwoAnnotations(existing, nil)
	assert.Equal(t, "keep", got["other/key"], "non-Kaiwo key preserved")
	_, hasKaiwo := got[KaiwoGpuPreemptionEnabledKey]
	assert.False(t, hasKaiwo, "Kaiwo key absent from nil manifest must be removed")
}
