// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package controller

import (
	"fmt"
	"regexp"
	"strings"
)

var invalidChars = regexp.MustCompile(`[^a-z0-9-]`)

// resourceName derives a stable, DNS-safe name for the InferencePool, AIGatewayRoute,
// and EPP objects created for a given InferenceService. The name encodes both namespace
// and resource name to avoid collisions across namespaces.
func resourceName(namespace, name string) string {
	raw := fmt.Sprintf("%s-%s", namespace, name)
	sanitized := invalidChars.ReplaceAllString(strings.ToLower(raw), "-")
	sanitized = strings.Trim(sanitized, "-")
	if len(sanitized) > 63 {
		sanitized = strings.TrimRight(sanitized[:63], "-")
	}
	return sanitized
}
