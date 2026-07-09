// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package common

const (
	Finalizer = "aigateway.silogen.ai/finalizer"

	DefaultManagedLabelName  = "app.kubernetes.io/managed-by"
	DefaultManagedLabelValue = "aim-engine"

	// DefaultModelNameAnnotation is the IS annotation key set by AIM-engine with
	// the actual vLLM-served model name (HF model ID).
	DefaultModelNameAnnotation = "aim.eai.amd.com/model-id"

	DefaultTargetNamespace  = "envoy-ai-gateway-system"
	DefaultGatewayName      = "https"
	DefaultGatewayNamespace = "envoy-gateway-system"

	DefaultHealthPort        = 8081
	DefaultInferencePoolPort = 8000
	DefaultEPPServicePort    = 9002
	DefaultEPPImage          = "registry.k8s.io/gateway-api-inference-extension/epp:v1.5.0-rc.2"

	FieldManager = "ai-gateway-discovery"

	DefaultAllowedGroupAnnotation = "cluster-auth/allowed-group"

	// Default timeouts applied to every generated AIGatewayRoute rule. LLM
	// completions routinely exceed Envoy AI Gateway's 60s nil-default (HTTP 504),
	// so both are set to 30m out of the box; override via the Helm chart.
	DefaultRequestTimeout        = "30m"
	DefaultBackendRequestTimeout = "30m"
)
