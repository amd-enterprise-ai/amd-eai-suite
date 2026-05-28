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
	DefaultResourceFlavourName  = "default-resource-flavor"
	DefaultCohortName           = "kaiwo"
	AMDGPUResource              = "amd.com/gpu"
	NVIDIAGPUResource           = "nvidia.com/gpu"
	CPUResource                 = "cpu"
	MemoryResource              = "memory"
	EphemeralStorageResource    = "ephemeral-storage"
)
