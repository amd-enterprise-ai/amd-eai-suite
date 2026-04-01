// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package secrets

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/go-logr/logr"
	corev1 "k8s.io/api/core/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
	"sigs.k8s.io/controller-runtime/pkg/client"

	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/secrets/common"
	"github.com/silogen/agent/internal/secrets/externalsecret"
)

type SecretHandler struct {
	clientset     kubernetes.Interface
	dynamicClient dynamic.Interface
	publisher     messaging.MessagePublisher
	logger        logr.Logger
}

func NewSecretHandler(
	clientset kubernetes.Interface,
	dynamicClient dynamic.Interface,
	publisher messaging.MessagePublisher,
	logger logr.Logger,
) *SecretHandler {
	return &SecretHandler{
		clientset:     clientset,
		dynamicClient: dynamicClient,
		publisher:     publisher,
		logger:        logger,
	}
}

// HandleCreate processes secret create messages.
func (h *SecretHandler) HandleCreate(ctx context.Context, msg *messaging.RawMessage) error {
	projectSecretID, secretType, scope, secretObj, err := parseCreateMessage(msg)
	if err != nil {
		h.logger.Error(err, "failed to parse create message", "payload", string(msg.Payload))
		return err
	}

	h.logger.Info("processing secret create",
		"project_secret_id", projectSecretID,
		"namespace", secretObj.GetNamespace(),
		"secret_name", secretObj.GetName(),
		"secret_type", secretType,
		"secret_scope", scope,
	)

	switch secretType {
	case messaging.SecretKindKubernetesSecret:
		secret, ok := secretObj.(*corev1.Secret)
		if !ok {
			return fmt.Errorf("unexpected object type for KubernetesSecret")
		}
		return h.createKubernetesSecret(ctx, secret)
	case messaging.SecretKindExternalSecret:
		obj, ok := secretObj.(*unstructured.Unstructured)
		if !ok {
			return fmt.Errorf("unexpected object type for ExternalSecret")
		}
		return h.createExternalSecret(ctx, obj)
	default:
		return fmt.Errorf("unsupported secret type: %s", secretType)
	}
}

// HandleDelete processes secret delete messages.
func (h *SecretHandler) HandleDelete(ctx context.Context, msg *messaging.RawMessage) error {
	deleteMsg, err := parseDeleteMessage(msg)
	if err != nil {
		h.logger.Error(err, "failed to parse delete message", "payload", string(msg.Payload))
		return err
	}

	h.logger.Info("processing secret delete",
		"project_secret_id", deleteMsg.ProjectSecretID,
		"namespace", deleteMsg.ProjectName,
		"secret_type", deleteMsg.SecretType,
		"secret_scope", deleteMsg.SecretScope,
	)

	switch deleteMsg.SecretType {
	case messaging.SecretKindKubernetesSecret:
		return h.deleteKubernetesSecrets(ctx, deleteMsg)
	case messaging.SecretKindExternalSecret:
		return h.deleteExternalSecrets(ctx, deleteMsg)
	default:
		h.logger.Info("WARN: unsupported secret type",
			"secret_type", deleteMsg.SecretType,
			"project_secret_id", deleteMsg.ProjectSecretID,
		)
		return fmt.Errorf("unsupported secret type: %s", deleteMsg.SecretType)
	}
}

// HandleUpdate is not supported for secrets.
func (h *SecretHandler) HandleUpdate(_ context.Context, _ *messaging.RawMessage) error {
	return errors.New("update operation not supported")
}

// parseCreateMessage unmarshals the create message payload, extracts metadata,
// and derives the project secret ID and scope from the manifest labels.
func parseCreateMessage(msg *messaging.RawMessage) (
	projectSecretID string,
	secretType messaging.SecretKind,
	scope *messaging.SecretScope,
	secretObj client.Object,
	err error,
) {
	var createMsg messaging.ProjectSecretsCreateMessage
	if err := json.Unmarshal(msg.Payload, &createMsg); err != nil {
		return "", "", nil, nil, fmt.Errorf("failed to parse create message: %w", err)
	}

	switch createMsg.SecretType {
	case messaging.SecretKindKubernetesSecret:
		var secret corev1.Secret
		if err := json.Unmarshal(createMsg.Manifest, &secret); err != nil {
			return "", "", nil, nil, fmt.Errorf("failed to parse secret manifest: %w", err)
		}
		secretObj = &secret
	case messaging.SecretKindExternalSecret:
		var obj unstructured.Unstructured
		if err := json.Unmarshal(createMsg.Manifest, &obj.Object); err != nil {
			return "", "", nil, nil, fmt.Errorf("failed to parse external secret manifest: %w", err)
		}
		secretObj = &obj
	default:
		return "", "", nil, nil, fmt.Errorf("unsupported secret type: %s", createMsg.SecretType)
	}

	labels := secretObj.GetLabels()
	if labels == nil {
		labels = map[string]string{}
		secretObj.SetLabels(labels)
	}

	id, ok := common.ExtractSecretID(labels)
	if !ok {
		return "", "", nil, nil, fmt.Errorf("manifest metadata is missing the %s label", common.ProjectSecretIDLabel)
	}

	scope = common.GetSecretScopeFromLabels(labels)
	if scope == nil {
		return "", "", nil, nil, fmt.Errorf("manifest metadata is missing the %s label", common.ProjectSecretScopeLabel)
	}

	return id, createMsg.SecretType, scope, secretObj, nil
}

// parseDeleteMessage unmarshals the delete message payload.
func parseDeleteMessage(msg *messaging.RawMessage) (*messaging.ProjectSecretsDeleteMessage, error) {
	var deleteMsg messaging.ProjectSecretsDeleteMessage
	if err := json.Unmarshal(msg.Payload, &deleteMsg); err != nil {
		return nil, fmt.Errorf("failed to parse delete message: %w", err)
	}
	return &deleteMsg, nil
}

// publishStatus is a helper to publish secret status messages.
func (h *SecretHandler) publishStatus(
	ctx context.Context,
	projectSecretID string,
	secretScope *messaging.SecretScope,
	status messaging.ProjectSecretStatus,
	reason string,
) {
	statusMsg := &messaging.ProjectSecretsUpdateMessage{
		MessageType:     messaging.MessageTypeProjectSecretsUpdate,
		ProjectSecretID: projectSecretID,
		SecretScope:     secretScope,
		Status:          status,
		StatusReason:    &reason,
		UpdatedAt:       time.Now().UTC(),
	}
	if err := h.publisher.Publish(ctx, statusMsg); err != nil {
		h.logger.Error(err, "failed to publish status")
	}
}

func (h *SecretHandler) createKubernetesSecret(
	ctx context.Context,
	secret *corev1.Secret,
) error {
	projectSecretID, _ := common.ExtractSecretID(secret.Labels)
	scope := common.GetSecretScopeFromLabels(secret.Labels)

	_, err := h.clientset.CoreV1().Secrets(secret.Namespace).Create(ctx, secret, metav1.CreateOptions{})
	if err != nil {
		if apierrors.IsAlreadyExists(err) {
			h.logger.Info("WARN: secret already exists",
				"secret_name", secret.Name,
				"namespace", secret.Namespace,
				"project_secret_id", projectSecretID,
			)
			return nil
		}

		h.logger.Error(err, "failed to create secret",
			"secret_name", secret.Name,
			"namespace", secret.Namespace,
			"project_secret_id", projectSecretID,
		)
		reason := fmt.Sprintf("Failed to create secret: %v", err)
		h.publishStatus(ctx, projectSecretID, scope, messaging.ProjectSecretStatusFailed, reason)
		return fmt.Errorf("failed to create secret: %w", err)
	}

	h.logger.Info("secret created",
		"secret_name", secret.Name,
		"namespace", secret.Namespace,
		"project_secret_id", projectSecretID,
	)
	return nil
}

func (h *SecretHandler) createExternalSecret(
	ctx context.Context,
	obj *unstructured.Unstructured,
) error {
	projectSecretID, _ := common.ExtractSecretID(obj.GetLabels())
	scope := common.GetSecretScopeFromLabels(obj.GetLabels())

	gvr, err := externalsecret.GetExternalSecretGVR(obj.GetAPIVersion())
	if err != nil {
		h.logger.Error(err, "invalid API version",
			"api_version", obj.GetAPIVersion(),
			"project_secret_id", projectSecretID,
		)
		reason := fmt.Sprintf("Invalid apiVersion '%s': %v", obj.GetAPIVersion(), err)
		h.publishStatus(ctx, projectSecretID, scope, messaging.ProjectSecretStatusFailed, reason)
		return fmt.Errorf("invalid API version: %w", err)
	}

	_, err = h.dynamicClient.Resource(gvr).Namespace(obj.GetNamespace()).Create(ctx, obj, metav1.CreateOptions{})
	if err != nil {
		if apierrors.IsAlreadyExists(err) {
			h.logger.Info("WARN: ExternalSecret already exists",
				"secret_name", obj.GetName(),
				"namespace", obj.GetNamespace(),
				"project_secret_id", projectSecretID,
			)
			return nil
		}

		h.logger.Error(err, "failed to create ExternalSecret",
			"secret_name", obj.GetName(),
			"namespace", obj.GetNamespace(),
			"project_secret_id", projectSecretID,
		)
		reason := fmt.Sprintf("Failed to create ExternalSecret: %v", err)
		h.publishStatus(ctx, projectSecretID, scope, messaging.ProjectSecretStatusFailed, reason)
		return fmt.Errorf("failed to create ExternalSecret: %w", err)
	}

	h.logger.Info("ExternalSecret created",
		"secret_name", obj.GetName(),
		"namespace", obj.GetNamespace(),
		"project_secret_id", projectSecretID,
	)

	return nil
}

func (h *SecretHandler) deleteKubernetesSecrets(ctx context.Context, deleteMsg *messaging.ProjectSecretsDeleteMessage) error {
	labelSelector := common.BuildLabelSelector(deleteMsg.ProjectSecretID)

	secretList, err := h.clientset.CoreV1().Secrets(deleteMsg.ProjectName).List(ctx, metav1.ListOptions{
		LabelSelector: labelSelector,
	})
	if err != nil {
		h.logger.Error(err, "failed to list secrets",
			"namespace", deleteMsg.ProjectName,
			"label_selector", labelSelector,
			"project_secret_id", deleteMsg.ProjectSecretID,
		)
		return fmt.Errorf("failed to list secrets: %w", err)
	}

	scope := &deleteMsg.SecretScope
	if len(secretList.Items) == 0 {
		h.logger.Info("no secrets found for deletion",
			"namespace", deleteMsg.ProjectName,
			"label_selector", labelSelector,
			"project_secret_id", deleteMsg.ProjectSecretID,
		)
		h.publishStatus(ctx, deleteMsg.ProjectSecretID, scope, messaging.ProjectSecretStatusDeleted, "No secrets found")
		return nil
	}

	err = h.clientset.CoreV1().Secrets(deleteMsg.ProjectName).DeleteCollection(
		ctx,
		metav1.DeleteOptions{},
		metav1.ListOptions{LabelSelector: labelSelector},
	)
	if err != nil {
		h.logger.Error(err, "failed to delete secrets (DeleteCollection)",
			"namespace", deleteMsg.ProjectName,
			"label_selector", labelSelector,
			"project_secret_id", deleteMsg.ProjectSecretID,
		)
		reason := fmt.Sprintf("Failed to delete secrets: %v", err)
		h.publishStatus(ctx, deleteMsg.ProjectSecretID, scope, messaging.ProjectSecretStatusDeleteFailed, reason)
		return fmt.Errorf("failed to delete secrets: %w", err)
	}

	h.logger.Info("secret deletion initiated",
		"count", len(secretList.Items),
		"project_secret_id", deleteMsg.ProjectSecretID,
	)

	return nil
}

func (h *SecretHandler) deleteExternalSecrets(ctx context.Context, deleteMsg *messaging.ProjectSecretsDeleteMessage) error {
	labelSelector := common.BuildLabelSelector(deleteMsg.ProjectSecretID)

	version, installed, derr := externalsecret.DiscoverExternalSecretVersion(ctx, h.dynamicClient)
	if derr != nil {
		h.logger.Error(derr, "failed to discover ExternalSecret version from CRD",
			"project_secret_id", deleteMsg.ProjectSecretID,
		)
		return derr
	}

	scope := &deleteMsg.SecretScope
	if !installed {
		h.publishStatus(ctx, deleteMsg.ProjectSecretID, scope, messaging.ProjectSecretStatusDeleted, "ExternalSecret CRD not installed; nothing to delete")
		return nil
	}

	gvr, err := externalsecret.GetExternalSecretGVR("external-secrets.io/" + version)
	if err != nil {
		return err
	}

	list, err := h.dynamicClient.Resource(gvr).Namespace(deleteMsg.ProjectName).List(ctx, metav1.ListOptions{
		LabelSelector: labelSelector,
	})
	if err != nil {
		h.logger.Error(err, "failed to list ExternalSecrets",
			"namespace", deleteMsg.ProjectName,
			"label_selector", labelSelector,
			"project_secret_id", deleteMsg.ProjectSecretID,
		)
		return fmt.Errorf("failed to list ExternalSecrets: %w", err)
	}

	if len(list.Items) == 0 {
		h.logger.Info("no ExternalSecrets found for deletion",
			"namespace", deleteMsg.ProjectName,
			"label_selector", labelSelector,
			"project_secret_id", deleteMsg.ProjectSecretID,
		)
		h.publishStatus(ctx, deleteMsg.ProjectSecretID, scope, messaging.ProjectSecretStatusDeleted, "No ExternalSecrets found")
		return nil
	}

	err = h.dynamicClient.Resource(gvr).Namespace(deleteMsg.ProjectName).DeleteCollection(
		ctx,
		metav1.DeleteOptions{},
		metav1.ListOptions{LabelSelector: labelSelector},
	)
	if err != nil {
		h.logger.Error(err, "failed to delete ExternalSecrets",
			"namespace", deleteMsg.ProjectName,
			"label_selector", labelSelector,
			"project_secret_id", deleteMsg.ProjectSecretID,
		)
		reason := fmt.Sprintf("Failed to delete ExternalSecrets: %v", err)
		h.publishStatus(ctx, deleteMsg.ProjectSecretID, scope, messaging.ProjectSecretStatusDeleteFailed, reason)
		return fmt.Errorf("failed to delete ExternalSecrets: %w", err)
	}

	h.logger.Info("ExternalSecret deletion initiated",
		"count", len(list.Items),
		"project_secret_id", deleteMsg.ProjectSecretID,
	)

	return nil
}
