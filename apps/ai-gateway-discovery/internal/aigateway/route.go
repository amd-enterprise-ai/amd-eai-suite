// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package aigateway

import (
	"github.com/silogen/ai-gateway-discovery/internal/config"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/utils/ptr"
)

// BuildAIGatewayRoute constructs a per-IS AIGatewayRoute with two routing rules:
//
//  1. x-ai-eg-backend: <aim-uuid> — precise routing via the AIM service UUID.
//     The Lua filter (set-model-header-from-body) extracts "backend" from the request
//     body and sets x-ai-eg-backend without setting x-ai-eg-model, so model-name
//     fallback rules in other HTTPRoutes cannot match. The UUID rule (two conditions:
//     Host + x-ai-eg-backend) beats catch-all rules on specificity regardless of
//     route creation order, making UUID routing deterministic across projects.
//
//  2. x-ai-eg-model: <model-name> — fallback for standard OpenAI-compatible clients
//     that do not include a "backend" field. Non-deterministic when the same model
//     name is deployed across multiple projects.
//
// The route is owned by the InferenceService via ownerReferences so Kubernetes GC
// deletes it automatically when the IS is deleted.
//
// When allowedGroup is non-empty, the route is annotated with
// cluster-auth/allowed-group so cluster-auth enforces group membership
// without a per-IS SecurityPolicy. cluster-auth/aim-service-id is always
// stamped so cluster-auth injects x-aim-service-id for metric attribution.
func BuildAIGatewayRoute(entry BackendEntry, cfg *config.ControllerConfig, allowedGroup string) *unstructured.Unstructured {
	obj := &unstructured.Unstructured{}
	obj.SetGroupVersionKind(AIGatewayRouteGVK)
	obj.SetName(entry.ResourceName)
	obj.SetNamespace(entry.ISNamespace)
	obj.SetOwnerReferences(isOwnerRef(entry))

	annotations := map[string]string{
		"cluster-auth/aim-service-id": entry.ISNamespace + "-" + entry.ISName,
	}
	if allowedGroup != "" {
		annotations["cluster-auth/allowed-group"] = allowedGroup
	}
	obj.SetAnnotations(annotations)

	_ = unstructured.SetNestedSlice(obj.Object, []interface{}{
		map[string]interface{}{
			"name":      cfg.GatewayName,
			"namespace": cfg.GatewayNamespace,
		},
	}, "spec", "parentRefs")

	_ = unstructured.SetNestedSlice(obj.Object, []interface{}{
		map[string]interface{}{"metadataKey": "llm_input_token", "type": "InputToken"},
		map[string]interface{}{"metadataKey": "llm_output_token", "type": "OutputToken"},
		map[string]interface{}{"metadataKey": "llm_total_token", "type": "TotalToken"},
	}, "spec", "llmRequestCosts")

	backendRef := []interface{}{
		map[string]interface{}{
			"group":     InferencePoolGVK.Group,
			"kind":      InferencePoolGVK.Kind,
			"name":      entry.ResourceName,
			"namespace": entry.ISNamespace,
		},
	}

	rules := []interface{}{}

	// UUID routing rule: matches on Host + x-ai-eg-backend + x-ai-eg-model (3 conditions).
	// Wins by specificity over the 2-condition model-name fallback rule in any HTTPRoute
	// regardless of creation order, so UUID routing is deterministic across projects.
	if entry.WorkloadID != "" {
		rules = append(rules, map[string]interface{}{
			"matches": []interface{}{
				map[string]interface{}{
					"headers": []interface{}{
						map[string]interface{}{"type": "Exact", "name": "Host", "value": cfg.AIRouteHostname},
						map[string]interface{}{"type": "Exact", "name": "x-ai-eg-backend", "value": entry.WorkloadID},
						map[string]interface{}{"type": "Exact", "name": "x-ai-eg-model", "value": entry.ModelName},
					},
				},
			},
			"backendRefs": backendRef,
			// LLM completions routinely run longer than Envoy AI Gateway's 60s
			// nil-timeouts default, which surfaces as HTTP 504 "upstream request
			// timeout". Set explicit timeouts (default 30m) on both the overall
			// request and each backend attempt; tunable via the Helm chart.
			"timeouts": map[string]interface{}{
				"request":        cfg.RequestTimeout,
				"backendRequest": cfg.BackendRequestTimeout,
			},
		})
	}

	// Model-name fallback for clients that do not send x-ai-eg-backend. Non-deterministic
	// when multiple AIMs serve the same model name.
	rules = append(rules, map[string]interface{}{
		"matches": []interface{}{
			map[string]interface{}{
				"headers": []interface{}{
					map[string]interface{}{"type": "Exact", "name": "Host", "value": cfg.AIRouteHostname},
					map[string]interface{}{"type": "Exact", "name": "x-ai-eg-model", "value": entry.ModelName},
				},
			},
		},
		"backendRefs": backendRef,
		// See above: avoid the 60s AI Gateway default that 504s long completions.
		"timeouts": map[string]interface{}{
			"request":        cfg.RequestTimeout,
			"backendRequest": cfg.BackendRequestTimeout,
		},
	})

	_ = unstructured.SetNestedSlice(obj.Object, rules, "spec", "rules")

	return obj
}

func isOwnerRef(entry BackendEntry) []metav1.OwnerReference {
	if entry.ISUID == types.UID("") {
		return nil
	}
	return []metav1.OwnerReference{
		{
			APIVersion:         InferenceServiceGVK.Group + "/" + InferenceServiceGVK.Version,
			Kind:               InferenceServiceGVK.Kind,
			Name:               entry.ISName,
			UID:                entry.ISUID,
			Controller:         ptr.To(true),
			BlockOwnerDeletion: ptr.To(true),
		},
	}
}
