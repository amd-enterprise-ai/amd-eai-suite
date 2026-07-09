// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package aigateway

import (
	"testing"

	"github.com/silogen/ai-gateway-discovery/internal/config"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
)

// TestBuildAIGatewayRoute_RulesCarryConfiguredTimeout guards against regressing
// to the Envoy AI Gateway 60s nil-timeouts default, which surfaced as HTTP 504
// "upstream request timeout" on long LLM completions. Every generated rule must
// carry the configured request/backendRequest timeouts. Non-default values are
// used here to prove the values propagate from config rather than being
// hardcoded.
func TestBuildAIGatewayRoute_RulesCarryConfiguredTimeout(t *testing.T) {
	const wantRequest, wantBackendRequest = "45m", "20m"
	cfg := &config.ControllerConfig{
		GatewayName:           "ai-gateway",
		GatewayNamespace:      "envoy-gateway-system",
		AIRouteHostname:       "gateway.example.com",
		RequestTimeout:        wantRequest,
		BackendRequestTimeout: wantBackendRequest,
	}

	cases := map[string]BackendEntry{
		"with-workload-id (uuid + fallback rules)": {
			ResourceName: "aim-abc",
			ISName:       "is-abc",
			ISNamespace:  "proj",
			ModelName:    "llama-3",
			WorkloadID:   "uuid-123",
		},
		"without-workload-id (fallback rule only)": {
			ResourceName: "aim-def",
			ISName:       "is-def",
			ISNamespace:  "proj",
			ModelName:    "llama-3",
		},
	}

	for name, entry := range cases {
		t.Run(name, func(t *testing.T) {
			obj := BuildAIGatewayRoute(entry, cfg, "")
			rules, found, err := unstructured.NestedSlice(obj.Object, "spec", "rules")
			if err != nil || !found {
				t.Fatalf("spec.rules missing: found=%v err=%v", found, err)
			}
			if len(rules) == 0 {
				t.Fatal("expected at least one rule")
			}
			for i, r := range rules {
				rule, ok := r.(map[string]interface{})
				if !ok {
					t.Fatalf("rule %d is not a map", i)
				}
				timeouts, ok := rule["timeouts"].(map[string]interface{})
				if !ok {
					t.Fatalf("rule %d missing timeouts", i)
				}
				if got := timeouts["request"]; got != wantRequest {
					t.Errorf("rule %d timeouts.request = %v, want %s", i, got, wantRequest)
				}
				if got := timeouts["backendRequest"]; got != wantBackendRequest {
					t.Errorf("rule %d timeouts.backendRequest = %v, want %s", i, got, wantBackendRequest)
				}
			}
		})
	}
}
