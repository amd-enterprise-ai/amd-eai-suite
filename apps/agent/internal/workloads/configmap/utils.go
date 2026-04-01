// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package configmap

import (
	corev1 "k8s.io/api/core/v1"

	"github.com/silogen/agent/internal/workloads/common"
)

// GetStatus extracts status from a ConfigMap resource.
func GetStatus(_ *corev1.ConfigMap) (string, string) {
	return common.StatusAdded, statusReasonAdded
}
