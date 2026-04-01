// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package common

// Kubernetes label keys used for secret management.
const (
	ProjectSecretIDLabel      = "airm.silogen.ai/project-secret-id"
	ProjectSecretScopeLabel   = "airm.silogen.ai/secret-scope"
	UseCaseLabel              = "airm.silogen.ai/use-case"
	ProjectSecretScopeProject = "Project"
)

const SecretFinalizer = "airm.silogen.ai/secret-finalizer"

const (
	ProjectSecretStatusUnknownReason  = "Secret status could not be determined."
	ProjectSecretStatusNotReadyReason = "Secret is not ready."
	ProjectSecretStatusReadyReason    = "Secret synced successfully."
)
