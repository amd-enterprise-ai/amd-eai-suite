// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package common

import (
	"fmt"

	"github.com/google/uuid"
	agent "github.com/silogen/agent/internal/common"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

// ComponentData holds the extracted metadata from a workload component.
type ComponentData struct {
	Name           string
	Kind           string
	APIVersion     string
	WorkloadID     uuid.UUID
	ComponentID    uuid.UUID
	ProjectID      uuid.UUID
	AutoDiscovered bool
	Submitter      *string
	WorkloadType   *string
}

// ExtractComponentData extracts workload metadata from a Kubernetes resource.
// Returns an error if required labels are missing or invalid.
func ExtractComponentData(obj client.Object) (*ComponentData, error) {
	labels := obj.GetLabels()
	if labels == nil {
		return nil, fmt.Errorf("resource has no labels")
	}

	// Extract workload-id
	workloadIDStr, ok := labels[WorkloadIDLabel]
	if !ok {
		return nil, fmt.Errorf("missing label: %s", WorkloadIDLabel)
	}
	workloadID, err := uuid.Parse(workloadIDStr)
	if err != nil {
		return nil, fmt.Errorf("invalid workload-id: %w", err)
	}

	// Extract component-id
	componentIDStr, ok := labels[ComponentIDLabel]
	if !ok {
		return nil, fmt.Errorf("missing label: %s", ComponentIDLabel)
	}
	componentID, err := uuid.Parse(componentIDStr)
	if err != nil {
		return nil, fmt.Errorf("invalid component-id: %w", err)
	}

	// Extract project-id (optional for now, but good to have)
	projectIDStr, ok := labels[agent.ProjectIDLabel]
	if !ok {
		return nil, fmt.Errorf("missing label: %s", agent.ProjectIDLabel)
	}
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		return nil, fmt.Errorf("invalid project-id: %w", err)
	}

	// Get GVK for APIVersion and Kind
	gvk := obj.GetObjectKind().GroupVersionKind()
	apiVersion := gvk.GroupVersion().String()
	kind := gvk.Kind

	// Extract workload-type (optional - Python handles validation and defaults)
	var workloadType *string
	if wt, ok := labels[WorkloadTypeLabel]; ok {
		workloadType = &wt
	}

	return &ComponentData{
		Name:           obj.GetName(),
		Kind:           kind,
		APIVersion:     apiVersion,
		WorkloadID:     workloadID,
		ComponentID:    componentID,
		ProjectID:      projectID,
		AutoDiscovered: agent.IsAutoDiscovered(obj),
		Submitter:      agent.ParseSubmitter(obj.GetAnnotations()),
		WorkloadType:   workloadType,
	}, nil
}
