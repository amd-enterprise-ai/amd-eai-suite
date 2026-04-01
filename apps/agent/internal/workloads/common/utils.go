// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package common

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"strings"

	"github.com/google/uuid"
	agent "github.com/silogen/agent/internal/common"
	"github.com/silogen/agent/internal/messaging"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/util/yaml"
	"k8s.io/client-go/dynamic"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
)

func HandleDeletion(
	ctx context.Context,
	c client.Client,
	publisher messaging.MessagePublisher,
	obj client.Object,
) error {
	if !controllerutil.ContainsFinalizer(obj, WorkloadFinalizer) {
		return nil
	}

	//nolint:errcheck
	data, _ := ExtractComponentData(obj)
	if data != nil {
		if err := PublishDeletionMessage(ctx, publisher, data); err != nil {
			return err
		}
	}

	return agent.RemoveFinalizer(ctx, c, obj, WorkloadFinalizer)
}

// WorkloadIDLabelSelector returns the label selector used to find all workload-owned resources.
func WorkloadIDLabelSelector(workloadID string) string {
	return fmt.Sprintf("%s=%s", WorkloadIDLabel, workloadID)
}

// DecodeYAMLDocuments decodes a YAML or JSON manifest into a list of unstructured objects.
//
// The manifest may contain multiple YAML documents separated by "---".
func DecodeYAMLDocuments(manifest string) ([]*unstructured.Unstructured, error) {
	dec := yaml.NewYAMLOrJSONDecoder(strings.NewReader(manifest), 4096)
	var objs []*unstructured.Unstructured

	for {
		var raw map[string]interface{}
		err := dec.Decode(&raw)
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, err
		}
		if len(raw) == 0 {
			continue
		}

		obj := &unstructured.Unstructured{Object: raw}
		// Set the GroupVersionKind.
		if obj.GetAPIVersion() != "" && obj.GetKind() != "" {
			gvk := schema.FromAPIVersionAndKind(obj.GetAPIVersion(), obj.GetKind())
			obj.SetGroupVersionKind(gvk)
		}
		objs = append(objs, obj)
	}

	return objs, nil
}

// ApplyObject creates one object using the dynamic client.
func ApplyObject(
	ctx context.Context,
	dynamicClient dynamic.Interface,
	mapper apimeta.RESTMapper,
	obj *unstructured.Unstructured,
) error {
	res, err := ResourceInterfaceForObject(dynamicClient, mapper, obj)
	if err != nil {
		return err
	}

	// Create the object
	_, err = res.Create(ctx, obj, metav1.CreateOptions{})
	return err
}

// ResourceInterfaceForObject resolves the object's GVK to a REST endpoint (GVR) and returns the
// dynamic ResourceInterface we can call.
//
// This uses discovery and may fail if the resource (e.g., a CRD) isn't installed.
func ResourceInterfaceForObject(
	dynamicClient dynamic.Interface,
	mapper apimeta.RESTMapper,
	obj *unstructured.Unstructured,
) (dynamic.ResourceInterface, error) {
	gvk := obj.GroupVersionKind()
	if gvk.Empty() {
		// Fall back to apiVersion/kind fields.
		if obj.GetAPIVersion() == "" || obj.GetKind() == "" {
			return nil, fmt.Errorf("object is missing apiVersion/kind")
		}
		gvk = schema.FromAPIVersionAndKind(obj.GetAPIVersion(), obj.GetKind())
	}

	mapping, err := mapper.RESTMapping(gvk.GroupKind(), gvk.Version)
	if err == nil {
		return resourceInterfaceFromMapping(dynamicClient, mapping, obj)
	}

	// If the resource is not found, try to map it to the empty version.
	mapping, err = mapper.RESTMapping(gvk.GroupKind(), "")
	if err != nil {
		return nil, err
	}
	return resourceInterfaceFromMapping(dynamicClient, mapping, obj)
}

func resourceInterfaceFromMapping(
	dynamicClient dynamic.Interface,
	mapping *apimeta.RESTMapping,
	obj *unstructured.Unstructured,
) (dynamic.ResourceInterface, error) {
	// For namespaced resources, the namespace is part of the request URL, so it must be present.
	res := dynamicClient.Resource(mapping.Resource)
	if mapping.Scope.Name() != apimeta.RESTScopeNameNamespace {
		return res, nil
	}

	ns := obj.GetNamespace()
	if ns == "" {
		return nil, fmt.Errorf(
			"namespaced object is missing metadata.namespace (kind=%s name=%s)",
			obj.GetKind(),
			obj.GetName(),
		)
	}
	return res.Namespace(ns), nil
}

// ParseDeleteWorkloadMessage parses and validates a DeleteWorkloadMessage from the raw message payload.
func ParseDeleteWorkloadMessage(msg *messaging.RawMessage) (messaging.DeleteWorkloadMessage, error) {
	var deleteMsg messaging.DeleteWorkloadMessage
	if err := json.Unmarshal(msg.Payload, &deleteMsg); err != nil {
		return messaging.DeleteWorkloadMessage{}, fmt.Errorf("failed to parse DeleteWorkloadMessage: %w", err)
	}
	if deleteMsg.WorkloadID == "" {
		return messaging.DeleteWorkloadMessage{}, fmt.Errorf("workload_id is required")
	}
	if _, err := uuid.Parse(deleteMsg.WorkloadID); err != nil {
		return messaging.DeleteWorkloadMessage{}, fmt.Errorf("invalid workload_id: %w", err)
	}
	return deleteMsg, nil
}
