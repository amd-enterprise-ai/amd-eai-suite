// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package config

import (
	"fmt"
	"os"
	"strconv"
	"time"

	"github.com/silogen/ai-gateway-discovery/internal/common"
)

type ControllerConfig struct {
	ManagedLabelName  string
	ManagedLabelValue string

	// ModelNameAnnotation is the IS annotation key set by AIM-engine with the
	// actual vLLM-served model name (HF model ID), used as the x-ai-eg-model
	// route match value.
	ModelNameAnnotation string

	TargetNamespace  string
	GatewayName      string
	GatewayNamespace string

	// AIRouteHostname is the Host header value added to every AIGatewayRoute.
	// Required — without it the route matches all hostnames on the shared Gateway.
	AIRouteHostname string
	HealthPort      int

	// EPP image and port for the inference-epp Deployment and Service the
	// controller creates in each InferenceService namespace.
	EPPImage          string
	EPPServicePort    int32
	InferencePoolPort int32

	// AllowedGroupAnnotation is the IS annotation key that carries the cluster-auth
	// group name. When set, the controller stamps cluster-auth/allowed-group on the
	// AIGatewayRoute so cluster-auth can enforce group membership without a per-IS
	// SecurityPolicy.
	AllowedGroupAnnotation string

	// RequestTimeout and BackendRequestTimeout are Gateway API duration strings
	// (e.g. "30m", "90s") set on every generated AIGatewayRoute rule. They guard
	// against Envoy AI Gateway's 60s nil-default that 504s long LLM completions.
	RequestTimeout        string
	BackendRequestTimeout string
}

func Load() (*ControllerConfig, error) {
	cfg := &ControllerConfig{
		ManagedLabelName:       getEnv("MANAGED_LABEL_NAME", common.DefaultManagedLabelName),
		ManagedLabelValue:      getEnv("MANAGED_LABEL_VALUE", common.DefaultManagedLabelValue),
		ModelNameAnnotation:    getEnv("MODEL_NAME_ANNOTATION", common.DefaultModelNameAnnotation),
		TargetNamespace:        getEnv("TARGET_NAMESPACE", common.DefaultTargetNamespace),
		GatewayName:            getEnv("GATEWAY_NAME", common.DefaultGatewayName),
		GatewayNamespace:       getEnv("GATEWAY_NAMESPACE", common.DefaultGatewayNamespace),
		AIRouteHostname:        os.Getenv("AI_ROUTE_HOSTNAME"),
		HealthPort:             getEnvAsInt("HEALTH_PORT", common.DefaultHealthPort),
		EPPImage:               getEnv("EPP_IMAGE", common.DefaultEPPImage),
		EPPServicePort:         int32(getEnvAsInt("EPP_SERVICE_PORT", common.DefaultEPPServicePort)),
		InferencePoolPort:      int32(getEnvAsInt("INFERENCE_POOL_PORT", common.DefaultInferencePoolPort)),
		AllowedGroupAnnotation: getEnv("ALLOWED_GROUP_ANNOTATION", common.DefaultAllowedGroupAnnotation),
		RequestTimeout:         getEnv("REQUEST_TIMEOUT", common.DefaultRequestTimeout),
		BackendRequestTimeout:  getEnv("BACKEND_REQUEST_TIMEOUT", common.DefaultBackendRequestTimeout),
	}

	if cfg.ManagedLabelName == "" {
		return nil, fmt.Errorf("MANAGED_LABEL_NAME must not be empty")
	}
	if cfg.GatewayName == "" {
		return nil, fmt.Errorf("GATEWAY_NAME must not be empty")
	}
	if cfg.AIRouteHostname == "" {
		return nil, fmt.Errorf("AI_ROUTE_HOSTNAME must not be empty: without a host filter the route matches all traffic on the shared Gateway")
	}
	if cfg.EPPImage == "" {
		return nil, fmt.Errorf("EPP_IMAGE must not be empty")
	}
	if _, err := time.ParseDuration(cfg.RequestTimeout); err != nil {
		return nil, fmt.Errorf("REQUEST_TIMEOUT %q is not a valid duration: %w", cfg.RequestTimeout, err)
	}
	if _, err := time.ParseDuration(cfg.BackendRequestTimeout); err != nil {
		return nil, fmt.Errorf("BACKEND_REQUEST_TIMEOUT %q is not a valid duration: %w", cfg.BackendRequestTimeout, err)
	}

	return cfg, nil
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func getEnvAsInt(name string, defaultVal int) int {
	if val, err := strconv.Atoi(os.Getenv(name)); err == nil {
		return val
	}
	return defaultVal
}
