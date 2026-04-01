// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package common

const (
	ProjectIDLabel = "airm.silogen.ai/project-id"

	SubmitterAnnotation      = "airm.silogen.ai/submitter"
	AutoDiscoveredAnnotation = "airm.silogen.ai/auto-discovered"
	AutoDiscoveredValue      = "true"

	ServiceAccountPrefix = "system:serviceaccount:"
	OIDCUserPrefix       = "oidc:"
	SubmitterMaxLength   = 256
)
