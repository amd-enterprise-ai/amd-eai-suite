// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package common

import (
	"github.com/google/uuid"
	agent "github.com/silogen/agent/internal/common"
	admissionv1 "k8s.io/api/admission/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/webhook/admission"
)

// ApplySecretTracking injects tracking labels and annotations onto a secret resource.
func ApplySecretTracking(obj client.Object, req admission.Request, nsCtx *agent.NamespaceContext) {
	hadTrackingID := ensureSecretIDLabel(obj, req)
	applySecretTrackingMetadata(obj, req, nsCtx.ProjectID, hadTrackingID)
}

// ensureSecretIDLabel ensures the project-secret-id label is present.
// On UPDATE, recovers the ID from the old object if missing.
// Returns true if the ID already existed (AIRM API created the secret).
func ensureSecretIDLabel(obj client.Object, req admission.Request) bool {
	labels := obj.GetLabels()
	if labels == nil {
		labels = make(map[string]string)
	}

	secretID := labels[ProjectSecretIDLabel]

	if secretID == "" && req.OldObject.Raw != nil {
		oldLabels := agent.GetLabelsFromRaw(req.OldObject.Raw)
		if oldID := oldLabels[ProjectSecretIDLabel]; oldID != "" {
			secretID = oldID
		}
	}

	idExisted := secretID != ""
	if secretID == "" {
		secretID = uuid.New().String()
	}

	labels[ProjectSecretIDLabel] = secretID
	obj.SetLabels(labels)

	return idExisted
}

// applySecretTrackingMetadata sets project-id, scope, and autodiscovery annotations.
func applySecretTrackingMetadata(obj client.Object, req admission.Request, nsProjectID string, hadTrackingID bool) {
	labels := obj.GetLabels()
	if labels == nil {
		labels = make(map[string]string)
	}
	annotations := obj.GetAnnotations()
	if annotations == nil {
		annotations = make(map[string]string)
	}

	if labels[agent.ProjectIDLabel] != nsProjectID {
		labels[agent.ProjectIDLabel] = nsProjectID
	}

	if labels[ProjectSecretScopeLabel] == "" {
		labels[ProjectSecretScopeLabel] = ProjectSecretScopeProject
	}

	isCreate := req.Operation == admissionv1.Create
	if !hadTrackingID && annotations[agent.AutoDiscoveredAnnotation] != agent.AutoDiscoveredValue {
		if annotations[agent.SubmitterAnnotation] == "" {
			annotations[agent.SubmitterAnnotation] = req.UserInfo.Username
		}
		annotations[agent.AutoDiscoveredAnnotation] = agent.AutoDiscoveredValue
	} else if isCreate && hadTrackingID {
		annotations[agent.AutoDiscoveredAnnotation] = "false"
	}

	obj.SetLabels(labels)
	obj.SetAnnotations(annotations)
}
