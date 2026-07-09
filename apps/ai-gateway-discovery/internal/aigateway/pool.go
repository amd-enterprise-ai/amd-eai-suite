// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package aigateway

import (
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
)

// EPPRef holds the name and port of the Endpoint Picker Plugin service.
// The EPP Service must live in the same namespace as the InferencePool —
// the InferencePool spec does not support cross-namespace endpointPickerRef.
type EPPRef struct {
	Name string
	Port int32
}

// BuildInferencePool constructs a gateway-api-inference-extension InferencePool
// that selects all KServe predictor pods for the given InferenceService.
// KServe stamps serving.kserve.io/inferenceservice=<name> on every predictor pod,
// making the selector stable across redeployments.
func BuildInferencePool(entry BackendEntry, epp EPPRef, targetPort int32) *unstructured.Unstructured {
	obj := &unstructured.Unstructured{}
	obj.SetGroupVersionKind(InferencePoolGVK)
	obj.SetName(entry.ResourceName)
	obj.SetNamespace(entry.ISNamespace)

	_ = unstructured.SetNestedMap(obj.Object, map[string]interface{}{
		"serving.kserve.io/inferenceservice": entry.ISName,
	}, "spec", "selector", "matchLabels")

	_ = unstructured.SetNestedSlice(obj.Object, []interface{}{
		map[string]interface{}{"number": int64(targetPort)},
	}, "spec", "targetPorts")

	_ = unstructured.SetNestedMap(obj.Object, map[string]interface{}{
		"name": epp.Name,
		"port": map[string]interface{}{
			"number": int64(epp.Port),
		},
	}, "spec", "endpointPickerRef")

	return obj
}
