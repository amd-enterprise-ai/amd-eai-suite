// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package nodes

import corev1 "k8s.io/api/core/v1"

const (
	GPUCapacityKey = "amd.com/gpu"

	GPUProductNameLabel     = "amd.com/gpu.product-name"
	GPUProductNameLabelBeta = "beta.amd.com/gpu.product-name"

	GPUDeviceIDLabel     = "amd.com/gpu.device-id"
	GPUDeviceIDLabelBeta = "beta.amd.com/gpu.device-id"

	GPUVRAMLabel     = "amd.com/gpu.vram"
	GPUVRAMLabelBeta = "beta.amd.com/gpu.vram"

	UnknownString = "Unknown"
)

var ProblematicNodeConditions = map[corev1.NodeConditionType]bool{
	corev1.NodeDiskPressure:       true,
	corev1.NodeMemoryPressure:     true,
	corev1.NodePIDPressure:        true,
	corev1.NodeNetworkUnavailable: true,
}
