// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package nodes

import (
	"math"
	"strconv"
	"strings"

	"github.com/silogen/agent/internal/messaging"
	corev1 "k8s.io/api/core/v1"
)

// getNodeStatus returns the node status string and readiness flag
func getNodeStatus(node *corev1.Node) (string, bool) {
	if len(node.Status.Conditions) == 0 {
		return UnknownString, false
	}

	var statusParts []string
	isReady := false

	// Check Ready condition
	for _, condition := range node.Status.Conditions {
		if condition.Type == corev1.NodeReady {
			if condition.Status == corev1.ConditionTrue {
				statusParts = append(statusParts, "Ready")
				isReady = true
			} else {
				statusParts = append(statusParts, "NotReady")
			}
			break
		}
	}

	// Check if node is schedulable
	if node.Spec.Unschedulable {
		statusParts = append(statusParts, "SchedulingDisabled")
		isReady = false
	}

	// If no status found yet, mark as Unknown
	if len(statusParts) == 0 {
		statusParts = append(statusParts, UnknownString)
	}

	// Check for problematic conditions
	for _, condition := range node.Status.Conditions {
		if ProblematicNodeConditions[condition.Type] && condition.Status == corev1.ConditionTrue {
			statusParts = append(statusParts, string(condition.Type))
		}
	}

	combinedStatus := strings.Join(statusParts, ", ")
	return combinedStatus, isReady
}

func getGPUInfo(node *corev1.Node) *messaging.GPUInformation {
	gpuCapacity, exists := node.Status.Capacity[GPUCapacityKey]
	if !exists {
		return nil
	}

	gpuCount := gpuCapacity.Value()
	if gpuCount == 0 {
		return nil
	}

	labels := node.Labels
	if labels == nil {
		labels = make(map[string]string)
	}

	// Extract GPU type (device ID)
	gpuType := UnknownString
	if val, ok := labels[GPUDeviceIDLabel]; ok {
		gpuType = val
	} else if val, ok := labels[GPUDeviceIDLabelBeta]; ok {
		gpuType = val
	}

	// Extract product name
	productName := UnknownString
	if val, ok := labels[GPUProductNameLabel]; ok {
		productName = strings.ReplaceAll(val, "_", " ")
	} else if val, ok := labels[GPUProductNameLabelBeta]; ok {
		productName = strings.ReplaceAll(val, "_", " ")
	}

	// Extract VRAM
	var vramBytes int64 = 0
	if val, ok := labels[GPUVRAMLabel]; ok {
		vramBytes = parseGPUVRAM(val)
	} else if val, ok := labels[GPUVRAMLabelBeta]; ok {
		vramBytes = parseGPUVRAM(val)
	}

	return &messaging.GPUInformation{
		Count:              int32(gpuCount),
		GPUType:            gpuType,
		Vendor:             messaging.GPUVendorAMD,
		VRAMBytesPerDevice: vramBytes,
		ProductName:        productName,
	}
}

// parseGPUVRAM parses GPU VRAM memory strings.
// Specialized parser for AMD GPU VRAM labels - Unlike standard Kubernetes memory units (Gi, Mi, etc.), AMD reports
// GPU VRAM using G, M, etc. (decimal-style suffixes) with binary semantics.
func parseGPUVRAM(vramStr string) int64 {
	if vramStr == "" {
		return 0
	}

	if val, err := strconv.ParseInt(vramStr, 10, 64); err == nil {
		return val
	}

	//nolint:staticcheck // QF1005: Using math.Pow for clarity and consistency across all unit definitions
	units := map[string]int64{
		// Binary units (IEC)
		"Ki": int64(math.Pow(1024, 1)),
		"Mi": int64(math.Pow(1024, 2)),
		"Gi": int64(math.Pow(1024, 3)),
		"Ti": int64(math.Pow(1024, 4)),
		"Pi": int64(math.Pow(1024, 5)),
		// AMD VRAM units (binary-based despite decimal-looking suffix)
		"K": int64(math.Pow(1024, 1)),
		"M": int64(math.Pow(1024, 2)),
		"G": int64(math.Pow(1024, 3)),
		"T": int64(math.Pow(1024, 4)),
		"P": int64(math.Pow(1024, 5)),
	}

	for suffix, multiplier := range units {
		if strings.HasSuffix(vramStr, suffix) {
			valueStr := strings.TrimSuffix(vramStr, suffix)
			if value, err := strconv.ParseFloat(valueStr, 64); err == nil {
				return int64(value * float64(multiplier))
			}
		}
	}

	// Try to parse as a float if nothing else worked
	if value, err := strconv.ParseFloat(vramStr, 64); err == nil {
		return int64(value)
	}

	return 0
}

// mapNodeToClusterNode converts a Kubernetes Node to a ClusterNode message
func mapNodeToClusterNode(node *corev1.Node) messaging.ClusterNode {

	cpuMilliCores := node.Status.Allocatable.Cpu().MilliValue()

	memoryBytes := node.Status.Allocatable.Memory().Value()

	ephemeralStorageBytes := node.Status.Allocatable.StorageEphemeral().Value()

	status, isReady := getNodeStatus(node)

	return messaging.ClusterNode{
		Name:                  node.Name,
		CPUMilliCores:         cpuMilliCores,
		MemoryBytes:           memoryBytes,
		EphemeralStorageBytes: ephemeralStorageBytes,
		GPUInformation:        getGPUInfo(node),
		Status:                status,
		IsReady:               isReady,
	}
}
