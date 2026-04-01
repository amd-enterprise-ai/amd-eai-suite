// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package quotas

import "k8s.io/apimachinery/pkg/runtime/schema"

var kaiwoQueueConfigGVR = schema.GroupVersionResource{
	Group: "kaiwo.silogen.ai", Version: "v1alpha1", Resource: "kaiwoqueueconfigs",
}

const (
	kaiwoQueueConfigFinalizer = "airm.silogen.ai/kaiwoqueueconfig-finalizer"

	KaiwoQueueConfigDefaultName = "kaiwo"
	KaiwoQueueConfigResource    = "kaiwoqueueconfigs"
	DefaultResourceFlavourName  = "default"
	DefaultCohortName           = "kaiwo"
	AMDGPUResource              = "amd.com/gpu"
	NVIDIAGPUResource           = "nvidia.com/gpu"
	CPUResource                 = "cpu"
	MemoryResource              = "memory"
	EphemeralStorageResource    = "ephemeral-storage"

	// Default topology for Kueue topology-aware scheduling
	DefaultTopologyName         = "default-topology"
	TopologyLevelBlockNodeLabel = "kaiwo/topology-block"
	TopologyLevelRackNodeLabel  = "kaiwo/topology-rack"
)
