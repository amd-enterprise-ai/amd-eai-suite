// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package quotas

import (
	"context"
	"testing"

	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/testutils"

	agent "github.com/silogen/agent/internal/common"
	kaiwov1alpha1 "github.com/silogen/kaiwo/apis/kaiwo/v1alpha1"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	clientgoscheme "k8s.io/client-go/kubernetes/scheme"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	kueuev1beta1 "sigs.k8s.io/kueue/apis/kueue/v1beta1"
)

func newTestScheme() *runtime.Scheme {
	s := runtime.NewScheme()
	_ = clientgoscheme.AddToScheme(s)
	_ = kaiwov1alpha1.AddToScheme(s)
	_ = kueuev1beta1.AddToScheme(s)
	return s
}

func TestBuildKaiwoQueueConfigManifest_NVIDIAGPUs(t *testing.T) {
	gpuVendor := agent.GPUVendorNVIDIA
	msg := &ClusterQuotasAllocationMessage{
		GPUVendor: &gpuVendor,
		QuotaAllocations: []ClusterQuotaAllocation{
			{
				QuotaName:             "test-quota",
				Namespaces:            []string{"default"},
				CPUMilliCores:         2000,
				MemoryBytes:           4294967296,
				EphemeralStorageBytes: 5368709120,
				GPUCount:              1,
			},
		},
		PriorityClasses: []PriorityClass{
			{Name: "normal", Priority: 50},
		},
	}

	config := buildKaiwoQueueConfigManifest(msg)

	assert.Equal(t, kaiwov1alpha1.GroupVersion.String(), config.APIVersion)
	assert.Equal(t, "KaiwoQueueConfig", config.Kind)
	assert.Equal(t, KaiwoQueueConfigDefaultName, config.Name)
	assert.Len(t, config.Spec.ClusterQueues, 1)
	assert.Len(t, config.Spec.WorkloadPriorityClasses, 1)

	cq := config.Spec.ClusterQueues[0]
	assert.Equal(t, "test-quota", cq.Name)
	assert.Equal(t, []string{"default"}, cq.Namespaces)
}

func TestBuildKaiwoQueueConfigManifest_AMDGPUs(t *testing.T) {
	gpuVendor := agent.GPUVendorAMD
	msg := &ClusterQuotasAllocationMessage{
		GPUVendor: &gpuVendor,
		QuotaAllocations: []ClusterQuotaAllocation{
			{
				QuotaName:             "amd-quota",
				Namespaces:            []string{"gpu-ns"},
				CPUMilliCores:         8000,
				MemoryBytes:           17179869184,
				EphemeralStorageBytes: 10737418240,
				GPUCount:              4,
			},
		},
		PriorityClasses: []PriorityClass{},
	}

	config := buildKaiwoQueueConfigManifest(msg)

	assert.Len(t, config.Spec.ClusterQueues, 1)
	cq := config.Spec.ClusterQueues[0]
	assert.Equal(t, "amd-quota", cq.Name)

	// Verify AMD GPU resource is included in covered resources
	assert.Len(t, cq.Spec.ResourceGroups, 1)
	rg := cq.Spec.ResourceGroups[0]
	assert.Contains(t, rg.CoveredResources, corev1.ResourceName(AMDGPUResource))
}

func TestBuildKaiwoQueueConfigManifest_NoGPUVendor(t *testing.T) {
	msg := &ClusterQuotasAllocationMessage{
		GPUVendor: nil,
		QuotaAllocations: []ClusterQuotaAllocation{
			{
				QuotaName:             "cpu-only",
				Namespaces:            []string{},
				CPUMilliCores:         1000,
				MemoryBytes:           2147483648,
				EphemeralStorageBytes: 5368709120,
				GPUCount:              0,
			},
		},
		PriorityClasses: []PriorityClass{},
	}

	config := buildKaiwoQueueConfigManifest(msg)

	assert.Len(t, config.Spec.ClusterQueues, 1)
	cq := config.Spec.ClusterQueues[0]

	// Verify only CPU, memory, ephemeral-storage are in covered resources
	rg := cq.Spec.ResourceGroups[0]
	assert.Len(t, rg.CoveredResources, 3)
	assert.Contains(t, rg.CoveredResources, corev1.ResourceName(CPUResource))
	assert.Contains(t, rg.CoveredResources, corev1.ResourceName(MemoryResource))
	assert.Contains(t, rg.CoveredResources, corev1.ResourceName(EphemeralStorageResource))
	assert.NotContains(t, rg.CoveredResources, corev1.ResourceName(AMDGPUResource))
	assert.NotContains(t, rg.CoveredResources, corev1.ResourceName(NVIDIAGPUResource))
}

func TestHandleDeletion_NoFinalizer(t *testing.T) {
	scheme := newTestScheme()
	now := metav1.Now()
	config := &kaiwov1alpha1.KaiwoQueueConfig{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-config",
			DeletionTimestamp: &now,
			Finalizers:        []string{"some-other-finalizer"},
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithRuntimeObjects(config).Build()
	pub := testutils.NewMockPublisher()

	err := HandleDeletion(context.Background(), c, pub, config)

	assert.NoError(t, err)
	assert.Empty(t, pub.Published)
}

func TestHandleDeletion_PublishesEmptyQuotasAndRemovesFinalizer(t *testing.T) {
	scheme := newTestScheme()
	now := metav1.Now()
	config := &kaiwov1alpha1.KaiwoQueueConfig{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-config",
			DeletionTimestamp: &now,
			Finalizers:        []string{kaiwoQueueConfigFinalizer},
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithRuntimeObjects(config).Build()
	pub := testutils.NewMockPublisher()

	err := HandleDeletion(context.Background(), c, pub, config)

	assert.NoError(t, err)

	require.Len(t, pub.Published, 1)
	msg, ok := pub.Published[0].(*ClusterQuotasStatusMessage)
	require.True(t, ok)
	assert.Equal(t, messaging.MessageTypeClusterQuotasStatusMessage, msg.MessageType)
	assert.NotNil(t, msg.QuotaAllocations)
	assert.Empty(t, msg.QuotaAllocations)

	assert.False(t, controllerutil.ContainsFinalizer(config, kaiwoQueueConfigFinalizer))
}

func TestHandleDeletion_PublishFails_RetainsFinalizer(t *testing.T) {
	scheme := newTestScheme()
	now := metav1.Now()
	config := &kaiwov1alpha1.KaiwoQueueConfig{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-config",
			DeletionTimestamp: &now,
			Finalizers:        []string{kaiwoQueueConfigFinalizer},
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithRuntimeObjects(config).Build()
	pub := testutils.NewMockFailingPublisher(assert.AnError)

	err := HandleDeletion(context.Background(), c, pub, config)

	assert.ErrorIs(t, err, assert.AnError)
	assert.Empty(t, pub.Published)
	assert.True(t, controllerutil.ContainsFinalizer(config, kaiwoQueueConfigFinalizer))
}
