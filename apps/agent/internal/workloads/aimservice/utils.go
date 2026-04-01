// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package aimservice

import (
	"fmt"

	aimv1alpha1 "github.com/amd-enterprise-ai/aim-engine/api/v1alpha1"
)

func GetStatus(svc *aimv1alpha1.AIMService) (string, string) {
	statusValue := string(svc.Status.Status)
	if statusValue == "" {
		return "", "Status information could not be determined"
	}

	return statusValue, fmt.Sprintf("AIMService status: %s", statusValue)
}
