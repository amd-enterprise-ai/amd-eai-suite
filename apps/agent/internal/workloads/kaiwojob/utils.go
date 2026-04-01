// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package kaiwojob

import (
	"fmt"

	kaiwov1alpha1 "github.com/silogen/kaiwo/apis/kaiwo/v1alpha1"
)

func GetStatus(kaiwoJob *kaiwov1alpha1.KaiwoJob) (string, string) {
	statusValue := string(kaiwoJob.Status.Status)
	if statusValue == "" {
		return "", "Status information could not be determined"
	}

	return statusValue, fmt.Sprintf("KaiwoJob status: %s", statusValue)
}
