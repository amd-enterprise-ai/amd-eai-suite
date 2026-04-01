// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package common

import (
	"context"
	"encoding/json"
	"net/http"
	"strings"

	"github.com/go-logr/logr"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/webhook/admission"
)

type NamespaceContext struct {
	ProjectID string
}

// GetProjectIdFromNamespace resolves the project-id label from a namespace.
// Returns nil if the namespace does not have the label (not managed by AIRM).
func GetProjectIdFromNamespace(ctx context.Context, c client.Client, namespace string) (*NamespaceContext, error) {
	ns := &corev1.Namespace{}
	if err := c.Get(ctx, client.ObjectKey{Name: namespace}, ns); err != nil {
		return nil, err
	}

	projectID, hasProjectID := ns.Labels[ProjectIDLabel]
	if !hasProjectID {
		return nil, nil
	}

	return &NamespaceContext{
		ProjectID: projectID,
	}, nil
}

// CreatePatchResponse builds a JSON patch admission response by comparing raw and mutated objects.
func CreatePatchResponse(req admission.Request, obj client.Object, logger logr.Logger) admission.Response {
	marshaledObj, err := json.Marshal(obj)
	if err != nil {
		return admission.Errored(http.StatusInternalServerError, err)
	}

	resp := admission.PatchResponseFromRaw(req.Object.Raw, marshaledObj)

	if len(resp.Patches) == 0 {
		logger.V(1).Info("resource already configured correctly", "kind", req.Kind.Kind)
		return admission.Allowed("resource already configured correctly")
	}

	logger.Info("applying mutations", "kind", req.Kind.Kind, "patches", len(resp.Patches))
	return resp
}

// GetLabelsFromRaw extracts labels from a raw JSON Kubernetes object.
func GetLabelsFromRaw(raw []byte) map[string]string {
	obj := &unstructured.Unstructured{}
	if err := json.Unmarshal(raw, &obj.Object); err != nil {
		return nil
	}
	return obj.GetLabels()
}

// IsAutoDiscovered checks if the object has the auto-discovered annotation set to "true".
func IsAutoDiscovered(obj client.Object) bool {
	annotations := obj.GetAnnotations()
	if annotations == nil {
		return false
	}
	return annotations[AutoDiscoveredAnnotation] == AutoDiscoveredValue
}

// ParseSubmitter extracts and normalizes the submitter annotation value.
func ParseSubmitter(annotations map[string]string) *string {
	if annotations == nil {
		return nil
	}

	submitter, ok := annotations[SubmitterAnnotation]
	if !ok || submitter == "" {
		return nil
	}

	if after, found := strings.CutPrefix(submitter, ServiceAccountPrefix); found {
		submitter = after
	}

	if after, found := strings.CutPrefix(submitter, OIDCUserPrefix); found {
		submitter = after
	}

	if submitter == "" {
		return nil
	}

	if len(submitter) > SubmitterMaxLength {
		submitter = submitter[:SubmitterMaxLength]
	}

	return &submitter
}
