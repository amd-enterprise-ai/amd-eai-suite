// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package kaiwoservice

import (
	"fmt"

	kaiwov1alpha1 "github.com/silogen/kaiwo/apis/kaiwo/v1alpha1"
)

func GetStatus(svc *kaiwov1alpha1.KaiwoService) (string, string) {
	statusValue := string(svc.Status.Status)
	if statusValue == "" {
		return "", "Status information could not be determined"
	}

	return statusValue, fmt.Sprintf("KaiwoService status: %s", statusValue)
}
