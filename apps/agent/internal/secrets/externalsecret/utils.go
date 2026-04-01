// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package externalsecret

import (
	"fmt"

	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/secrets/common"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

// GetExternalSecretStatus extracts the status from an ExternalSecret's conditions.
// Supports unstructured ExternalSecrets (any served version).
func GetExternalSecretStatus(obj client.Object) (messaging.ProjectSecretStatus, string) {
	u, ok := obj.(*unstructured.Unstructured)
	if !ok || u == nil {
		return "", common.ProjectSecretStatusUnknownReason
	}

	conditions, found, err := unstructured.NestedSlice(u.Object, "status", "conditions")
	if err != nil || !found || len(conditions) == 0 {
		return "", common.ProjectSecretStatusUnknownReason
	}

	for _, c := range conditions {
		m, ok := c.(map[string]interface{})
		if !ok {
			continue
		}

		condStatus, message, reason, isReadyCond, condErr := parseReadyCondition(m)
		if condErr != nil || !isReadyCond {
			continue
		}
		return statusFromReadyCondition(condStatus, message, reason)
	}

	return messaging.ProjectSecretStatusUnknown, common.ProjectSecretStatusUnknownReason
}

func parseReadyCondition(m map[string]interface{}) (corev1.ConditionStatus, string, string, bool, error) {
	condType, _, err := unstructured.NestedString(m, "type")
	if err != nil {
		return "", "", "", false, err
	}
	if condType != "Ready" {
		return "", "", "", false, nil
	}

	statusStr, _, err := unstructured.NestedString(m, "status")
	if err != nil {
		return "", "", "", true, err
	}
	message, _, err := unstructured.NestedString(m, "message")
	if err != nil {
		return "", "", "", true, err
	}
	reason, _, err := unstructured.NestedString(m, "reason")
	if err != nil {
		return "", "", "", true, err
	}
	return corev1.ConditionStatus(statusStr), message, reason, true, nil
}

// GetExternalSecretGVR returns the GroupVersionResource for ExternalSecrets.
func GetExternalSecretGVR(apiVersion string) (schema.GroupVersionResource, error) {
	if apiVersion == "" {
		return schema.GroupVersionResource{}, fmt.Errorf("apiVersion is required to build ExternalSecret GVR")
	}
	gv, err := schema.ParseGroupVersion(apiVersion)
	if err != nil {
		return schema.GroupVersionResource{}, err
	}
	return schema.GroupVersionResource{
		Group:    gv.Group,
		Version:  gv.Version,
		Resource: "externalsecrets",
	}, nil
}

func statusFromReadyCondition(
	condStatus corev1.ConditionStatus,
	message string,
	reason string,
) (messaging.ProjectSecretStatus, string) {
	switch condStatus {
	case corev1.ConditionTrue:
		if message != "" {
			return messaging.ProjectSecretStatusSynced, message
		}
		return messaging.ProjectSecretStatusSynced, common.ProjectSecretStatusReadyReason
	case corev1.ConditionFalse:
		if message != "" {
			return messaging.ProjectSecretStatusSyncedError, message
		}
		if reason != "" {
			return messaging.ProjectSecretStatusSyncedError, reason
		}
		return messaging.ProjectSecretStatusSyncedError, common.ProjectSecretStatusNotReadyReason
	case corev1.ConditionUnknown:
		if message != "" {
			return messaging.ProjectSecretStatusUnknown, message
		}
		return messaging.ProjectSecretStatusUnknown, common.ProjectSecretStatusUnknownReason
	default:
		return messaging.ProjectSecretStatusUnknown, common.ProjectSecretStatusUnknownReason
	}
}
