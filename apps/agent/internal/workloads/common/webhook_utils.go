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

func ApplyWorkloadTracking(obj client.Object, req admission.Request, nsCtx *agent.NamespaceContext) {
	hadTrackingIds := ensureWorkloadAndComponentIDLabels(obj, req)
	applyTrackingMetadata(obj, req, nsCtx.ProjectID, hadTrackingIds)
}

func EnsureKueueLabel(obj client.Object, namespace string) {
	labels := obj.GetLabels()
	if labels == nil {
		labels = make(map[string]string)
	}
	labels[KueueNameLabel] = namespace
	obj.SetLabels(labels)
}

func ensureWorkloadAndComponentIDLabels(obj client.Object, req admission.Request) bool {
	labels := obj.GetLabels()
	if labels == nil {
		labels = make(map[string]string)
	}

	workloadID := labels[WorkloadIDLabel]
	componentID := labels[ComponentIDLabel]

	if (workloadID == "" || componentID == "") && req.OldObject.Raw != nil {
		oldLabels := agent.GetLabelsFromRaw(req.OldObject.Raw)
		if workloadID == "" {
			workloadID = oldLabels[WorkloadIDLabel]
		}
		if componentID == "" {
			componentID = oldLabels[ComponentIDLabel]
		}
	}

	idsExisted := workloadID != "" && componentID != ""
	if workloadID == "" {
		workloadID = uuid.New().String()
	}
	if componentID == "" {
		componentID = uuid.New().String()
	}

	labels[WorkloadIDLabel] = workloadID
	labels[ComponentIDLabel] = componentID
	obj.SetLabels(labels)

	return idsExisted
}

func applyTrackingMetadata(obj client.Object, req admission.Request, nsProjectID string, hadTrackingIds bool) {
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

	isCreate := req.Operation == admissionv1.Create
	if !hadTrackingIds && annotations[agent.AutoDiscoveredAnnotation] != agent.AutoDiscoveredValue {
		if annotations[agent.SubmitterAnnotation] == "" {
			annotations[agent.SubmitterAnnotation] = req.UserInfo.Username
		}
		annotations[agent.AutoDiscoveredAnnotation] = agent.AutoDiscoveredValue
	} else if isCreate && hadTrackingIds {
		annotations[agent.AutoDiscoveredAnnotation] = "false"
	}

	obj.SetLabels(labels)
	obj.SetAnnotations(annotations)
}

func PropagateTrackingLabelsToTemplate(source client.Object, templateLabels map[string]string) map[string]string {
	if templateLabels == nil {
		templateLabels = make(map[string]string)
	}
	sourceLabels := source.GetLabels()
	templateLabels[WorkloadIDLabel] = sourceLabels[WorkloadIDLabel]
	templateLabels[ComponentIDLabel] = sourceLabels[ComponentIDLabel]
	return templateLabels
}
