// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package configmap

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/go-logr/logr"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"

	"github.com/silogen/agent/internal/messaging"
)

// ConfigMapHandler handles configmap create/delete messages.
type ConfigMapHandler struct {
	clientset kubernetes.Interface
	publisher messaging.MessagePublisher
	logger    logr.Logger
}

// NewConfigMapHandler creates a new ConfigMapHandler.
func NewConfigMapHandler(clientset kubernetes.Interface, publisher messaging.MessagePublisher, logger logr.Logger) *ConfigMapHandler {
	return &ConfigMapHandler{
		clientset: clientset,
		publisher: publisher,
		logger:    logger,
	}
}

// HandleCreate processes storage create messages.
func (h *ConfigMapHandler) HandleCreate(ctx context.Context, msg *messaging.RawMessage) error {
	var createMsg messaging.ProjectS3StorageCreateMessage
	if err := json.Unmarshal(msg.Payload, &createMsg); err != nil {
		h.logger.Error(err, "failed to parse create message", "payload", string(msg.Payload))
		return fmt.Errorf("failed to parse message: %w", err)
	}

	if createMsg.Manifest == "" {
		return fmt.Errorf("manifest is required")
	}

	h.logger.Info("processing storage create",
		"project_name", createMsg.ProjectName,
		"storage_id", createMsg.ProjectStorageID,
	)

	configMap, err := parseConfigMapManifest(createMsg.Manifest)
	if err != nil {
		return fmt.Errorf("failed to prepare configmap: %w", err)
	}

	// Create ConfigMap in Kubernetes
	_, err = h.clientset.CoreV1().ConfigMaps(createMsg.ProjectName).Create(ctx, configMap, metav1.CreateOptions{})
	if err != nil {
		if apierrors.IsAlreadyExists(err) {
			h.logger.Info("configmap already exists",
				"configmap", configMap.Name,
				"namespace", createMsg.ProjectName,
				"storage_id", createMsg.ProjectStorageID,
			)
			return nil
		}

		h.logger.Error(err, "failed to create configmap",
			"configmap", configMap.Name,
			"namespace", createMsg.ProjectName,
			"storage_id", createMsg.ProjectStorageID,
		)

		// Publish failure status
		h.publishStatus(ctx, createMsg.ProjectStorageID, messaging.ConfigMapStatusFailed,
			fmt.Sprintf("Failed to create ConfigMap: %v", err))

		return fmt.Errorf("failed to create configmap: %w", err)
	}

	h.logger.Info("configmap created",
		"configmap", configMap.Name,
		"namespace", createMsg.ProjectName,
		"storage_id", createMsg.ProjectStorageID,
	)

	// Controller will catch the Add event and publish status
	return nil
}

// HandleDelete processes storage delete messages.
func (h *ConfigMapHandler) HandleDelete(ctx context.Context, msg *messaging.RawMessage) error {
	var deleteMsg messaging.ProjectStorageDeleteMessage
	if err := json.Unmarshal(msg.Payload, &deleteMsg); err != nil {
		h.logger.Error(err, "failed to parse delete message", "payload", string(msg.Payload))
		return fmt.Errorf("failed to parse message: %w", err)
	}

	h.logger.Info("processing storage delete",
		"project_name", deleteMsg.ProjectName,
		"storage_id", deleteMsg.ProjectStorageID,
	)

	labelSelector := fmt.Sprintf("%s=%s", ProjectStorageIDLabel, deleteMsg.ProjectStorageID)

	// Check if any ConfigMaps exist with this label
	existingCMs, err := h.clientset.CoreV1().ConfigMaps(deleteMsg.ProjectName).List(
		ctx,
		metav1.ListOptions{LabelSelector: labelSelector},
	)
	if err != nil {
		h.logger.Error(err, "failed to list configmaps",
			"namespace", deleteMsg.ProjectName,
			"label_selector", labelSelector,
		)
		return fmt.Errorf("failed to list configmaps: %w", err)
	}

	// If no ConfigMaps exist, publish Deleted status immediately
	if len(existingCMs.Items) == 0 {
		h.logger.Info("no configmaps found, publishing deleted status",
			"namespace", deleteMsg.ProjectName,
			"storage_id", deleteMsg.ProjectStorageID,
		)
		h.publishStatus(ctx, deleteMsg.ProjectStorageID, messaging.ConfigMapStatusDeleted,
			"ConfigMap not found (already deleted)")
		return nil
	}

	// Delete ConfigMaps by label selector
	err = h.clientset.CoreV1().ConfigMaps(deleteMsg.ProjectName).DeleteCollection(
		ctx,
		metav1.DeleteOptions{},
		metav1.ListOptions{LabelSelector: labelSelector},
	)
	if err != nil {
		h.logger.Error(err, "failed to delete configmaps",
			"namespace", deleteMsg.ProjectName,
			"label_selector", labelSelector,
		)

		// Publish failure status
		h.publishStatus(ctx, deleteMsg.ProjectStorageID, messaging.ConfigMapStatusFailed,
			fmt.Sprintf("Failed to delete ConfigMaps: %v", err))

		return fmt.Errorf("failed to delete configmaps: %w", err)
	}

	h.logger.Info("configmap deletion initiated",
		"namespace", deleteMsg.ProjectName,
		"label_selector", labelSelector,
	)

	// Controller will catch the Delete event and publish status
	return nil
}

// HandleUpdate is not supported for ConfigMaps.
func (h *ConfigMapHandler) HandleUpdate(_ context.Context, _ *messaging.RawMessage) error {
	return errors.New("update operation not supported")
}

func (h *ConfigMapHandler) publishStatus(ctx context.Context, storageID string, status messaging.ConfigMapStatus, reason string) {
	statusMsg := &messaging.ProjectStorageUpdateMessage{
		MessageType:      messaging.MessageTypeProjectStorageUpdate,
		ProjectStorageID: storageID,
		Status:           status,
		StatusReason:     &reason,
		UpdatedAt:        time.Now().UTC(),
	}
	if err := h.publisher.Publish(ctx, statusMsg); err != nil {
		h.logger.Error(err, "failed to publish status")
	}
}
