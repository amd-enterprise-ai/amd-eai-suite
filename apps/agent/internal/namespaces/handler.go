// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package namespaces

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"

	"github.com/go-logr/logr"
	corev1 "k8s.io/api/core/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"

	"github.com/silogen/agent/internal/messaging"
)

// NamespaceHandler handles namespace create/delete messages.
type NamespaceHandler struct {
	clientset kubernetes.Interface
	publisher messaging.MessagePublisher
	logger    logr.Logger
}

// NewNamespaceHandler creates a new NamespaceHandler.
func NewNamespaceHandler(clientset kubernetes.Interface, publisher messaging.MessagePublisher, logger logr.Logger) *NamespaceHandler {
	return &NamespaceHandler{
		clientset: clientset,
		publisher: publisher,
		logger:    logger,
	}
}

// HandleCreate processes namespace create messages.
func (h *NamespaceHandler) HandleCreate(ctx context.Context, msg *messaging.RawMessage) error {
	namespace, projectID, err := parseCreateMessage(msg)
	if err != nil {
		h.logger.Error(err, "failed to parse create message", "payload", string(msg.Payload))
		return err
	}

	h.logger.Info("processing namespace create",
		"namespace", namespace.Name,
		"project_id", projectID,
	)

	_, err = h.clientset.CoreV1().Namespaces().Create(ctx, namespace, metav1.CreateOptions{})
	if err != nil {
		reason := fmt.Sprintf("Failed to create namespace: %v", err)
		h.logger.Error(err, "failed to create namespace",
			"namespace", namespace.Name,
			"project_id", projectID,
			"reason", reason,
		)
		h.publishStatus(ctx, projectID, messaging.NamespaceStatusFailed, reason)
		return fmt.Errorf("failed to create namespace: %w", err)
	}

	h.logger.Info("namespace created",
		"namespace", namespace.Name,
		"project_id", projectID,
	)

	// Informer will catch the Add event and publish status based on actual K8s phase
	return nil
}

// HandleDelete processes namespace delete messages.
func (h *NamespaceHandler) HandleDelete(ctx context.Context, msg *messaging.RawMessage) error {
	name, projectID, err := parseDeleteMessage(msg)
	if err != nil {
		h.logger.Error(err, "failed to parse delete message", "payload", string(msg.Payload))
		return err
	}

	h.logger.Info("processing namespace delete",
		"namespace", name,
		"project_id", projectID,
	)

	// Verify namespace exists and has correct project_id label
	ns, err := h.clientset.CoreV1().Namespaces().Get(ctx, name, metav1.GetOptions{})
	if err != nil {
		return h.handleGetNamespaceError(ctx, err, name, projectID)
	}

	// Verify project_id label matches
	if err := validateProjectIDLabel(ns, projectID); err != nil {
		h.logger.Info("WARN: namespace project_id label mismatch",
			"namespace", name,
			"expected_project_id", projectID,
			"actual_project_id", extractProjectIDFromNamespace(ns),
		)
		h.publishStatus(ctx, projectID, messaging.NamespaceStatusDeleted, "Namespace project_id label mismatch")
		return nil
	}

	// Delete namespace
	if err := h.clientset.CoreV1().Namespaces().Delete(ctx, name, metav1.DeleteOptions{}); err != nil {
		return h.handleDeleteNamespaceError(ctx, err, name, projectID)
	}

	h.logger.Info("namespace deletion initiated",
		"namespace", name,
		"project_id", projectID,
	)

	// Informer will catch the Delete event and publish DELETED status
	return nil
}

// parseCreateMessage unmarshals the create message and extracts namespace and project ID.
func parseCreateMessage(msg *messaging.RawMessage) (*corev1.Namespace, string, error) {
	var createMsg messaging.ProjectNamespaceCreateMessage
	if err := json.Unmarshal(msg.Payload, &createMsg); err != nil {
		return nil, "", fmt.Errorf("failed to parse create message: %w", err)
	}

	var namespace corev1.Namespace
	if err := json.Unmarshal(createMsg.NamespaceManifest, &namespace); err != nil {
		return nil, "", fmt.Errorf("failed to parse create namespace manifest: %w", err)
	}

	projectID := extractProjectIDFromNamespace(&namespace)
	return &namespace, projectID, nil
}

// parseDeleteMessage unmarshals the delete message and extracts namespace name and project ID.
func parseDeleteMessage(msg *messaging.RawMessage) (name, projectID string, err error) {
	var deleteMsg messaging.ProjectNamespaceDeleteMessage
	if unmarshalErr := json.Unmarshal(msg.Payload, &deleteMsg); unmarshalErr != nil {
		return "", "", fmt.Errorf("failed to parse delete message: %w", unmarshalErr)
	}
	return deleteMsg.Name, deleteMsg.ProjectID, nil
}

// validateProjectIDLabel checks if the namespace belongs to the expected project.
func validateProjectIDLabel(ns *corev1.Namespace, expectedProjectID string) error {
	actualProjectID := extractProjectIDFromNamespace(ns)
	if actualProjectID == "" || actualProjectID != expectedProjectID {
		return fmt.Errorf("project_id mismatch: expected %s, got %s", expectedProjectID, actualProjectID)
	}
	return nil
}

// handleGetNamespaceError handles errors from Get operation.
func (h *NamespaceHandler) handleGetNamespaceError(ctx context.Context, err error, namespaceName, projectID string) error {
	if apierrors.IsNotFound(err) {
		h.logger.Info("namespace not found",
			"namespace", namespaceName,
			"project_id", projectID,
		)
		h.publishStatus(ctx, projectID, messaging.NamespaceStatusDeleted, "Namespace not found")
		return nil
	}

	h.logger.Error(err, "failed to get namespace", "namespace", namespaceName)
	return fmt.Errorf("failed to get namespace: %w", err)
}

// handleDeleteNamespaceError handles errors from Delete operation.
func (h *NamespaceHandler) handleDeleteNamespaceError(ctx context.Context, err error, namespaceName, projectID string) error {
	if apierrors.IsNotFound(err) {
		h.logger.Info("namespace already deleted",
			"namespace", namespaceName,
			"project_id", projectID,
		)
		h.publishStatus(ctx, projectID, messaging.NamespaceStatusDeleted, "Namespace already deleted")
		return nil
	}

	h.logger.Error(err, "failed to delete namespace",
		"namespace", namespaceName,
		"project_id", projectID,
	)

	reason := fmt.Sprintf("Failed to delete namespace: %v", err)
	h.publishStatus(ctx, projectID, messaging.NamespaceStatusDeleteFailed, reason)
	return fmt.Errorf("failed to delete namespace: %w", err)
}

// publishStatus is a helper to publish namespace status messages.
func (h *NamespaceHandler) publishStatus(ctx context.Context, projectID string, status messaging.NamespaceStatus, reason string) {
	statusMsg := &messaging.ProjectNamespaceStatusMessage{
		MessageType:  messaging.MessageTypeProjectNamespaceStatus,
		ProjectID:    projectID,
		Status:       status,
		StatusReason: &reason,
	}
	if err := h.publisher.Publish(ctx, statusMsg); err != nil {
		h.logger.Error(err, "failed to publish status")
	}
}

func (h *NamespaceHandler) HandleUpdate(_ context.Context, _ *messaging.RawMessage) error {
	return errors.New("update operation not supported")
}
