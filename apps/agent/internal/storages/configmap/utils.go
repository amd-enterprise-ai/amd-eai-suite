// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package configmap

import (
	"context"
	"fmt"
	"time"

	agent "github.com/silogen/agent/internal/common"
	"github.com/silogen/agent/internal/messaging"
	corev1 "k8s.io/api/core/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	"sigs.k8s.io/yaml"
)

// parseConfigMapManifest unmarshals the YAML manifest into a typed ConfigMap.
// Namespace and labels are set by the API when building the manifest.
func parseConfigMapManifest(manifest string) (*corev1.ConfigMap, error) {
	var cm corev1.ConfigMap
	if err := yaml.Unmarshal([]byte(manifest), &cm); err != nil {
		return nil, fmt.Errorf("failed to parse configmap manifest: %w", err)
	}

	return &cm, nil
}

func HandleDeletion(
	ctx context.Context,
	c client.Client,
	publisher messaging.MessagePublisher,
	obj client.Object,
) error {
	if !controllerutil.ContainsFinalizer(obj, ConfigMapFinalizer) {
		return nil
	}

	labels := obj.GetLabels()
	if storageID, ok := labels[ProjectStorageIDLabel]; ok {
		if err := publishStorageStatus(ctx, publisher, storageID, messaging.ConfigMapStatusDeleted, "ConfigMap deleted."); err != nil {
			return err
		}
	}

	return agent.RemoveFinalizer(ctx, c, obj, ConfigMapFinalizer)
}

func publishStorageStatus(ctx context.Context, publisher messaging.MessagePublisher, storageID string, status messaging.ConfigMapStatus, reason string) error {
	msg := &messaging.ProjectStorageUpdateMessage{
		MessageType:      messaging.MessageTypeProjectStorageUpdate,
		ProjectStorageID: storageID,
		Status:           status,
		StatusReason:     &reason,
		UpdatedAt:        time.Now().UTC(),
	}
	return publisher.Publish(ctx, msg)
}
