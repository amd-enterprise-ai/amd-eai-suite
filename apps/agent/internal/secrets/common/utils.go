// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package common

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/google/uuid"
	agent "github.com/silogen/agent/internal/common"
	"github.com/silogen/agent/internal/messaging"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
)

// SecretData holds extracted metadata from an auto-discovered secret.
type SecretData struct {
	Name           string
	SecretID       uuid.UUID
	ProjectID      uuid.UUID
	Kind           messaging.SecretKind
	UseCase        *string
	Scope          *messaging.SecretScope
	AutoDiscovered bool
	Submitter      *string
}

// ExtractSecretData extracts autodiscovery metadata from a Kubernetes resource's labels and annotations.
func ExtractSecretData(obj client.Object, kind messaging.SecretKind) (*SecretData, error) {
	labels := obj.GetLabels()
	if labels == nil {
		return nil, fmt.Errorf("resource has no labels")
	}

	secretIDStr, ok := labels[ProjectSecretIDLabel]
	if !ok {
		return nil, fmt.Errorf("missing label: %s", ProjectSecretIDLabel)
	}
	secretID, err := uuid.Parse(secretIDStr)
	if err != nil {
		return nil, fmt.Errorf("invalid secret-id: %w", err)
	}

	projectIDStr, ok := labels[agent.ProjectIDLabel]
	if !ok {
		return nil, fmt.Errorf("missing label: %s", agent.ProjectIDLabel)
	}
	projectID, err := uuid.Parse(projectIDStr)
	if err != nil {
		return nil, fmt.Errorf("invalid project-id: %w", err)
	}

	useCase := GetSecretUseCaseFromLabels(labels)

	return &SecretData{
		Name:           obj.GetName(),
		SecretID:       secretID,
		ProjectID:      projectID,
		Kind:           kind,
		UseCase:        useCase,
		Scope:          GetSecretScopeFromLabels(labels),
		AutoDiscovered: agent.IsAutoDiscovered(obj),
		Submitter:      agent.ParseSubmitter(obj.GetAnnotations()),
	}, nil
}

// PublishAutoDiscoveryMessage publishes an auto-discovered secret message.
func PublishAutoDiscoveryMessage(
	ctx context.Context,
	publisher messaging.MessagePublisher,
	data *SecretData,
) error {
	msg := &messaging.AutoDiscoveredSecretMessage{
		MessageType: messaging.MessageTypeAutoDiscoveredSecret,
		ProjectID:   data.ProjectID.String(),
		SecretID:    data.SecretID.String(),
		Name:        data.Name,
		Kind:        data.Kind,
		UseCase:     data.UseCase,
		Submitter:   data.Submitter,
		UpdatedAt:   time.Now().UTC(),
	}
	return publisher.Publish(ctx, msg)
}

// BuildLabelSelector creates a label selector string for a project secret ID.
func BuildLabelSelector(projectSecretID string) string {
	return ProjectSecretIDLabel + "=" + projectSecretID
}

// ExtractSecretID returns the project-secret-id label value and whether it was present.
func ExtractSecretID(labels map[string]string) (string, bool) {
	if labels == nil {
		return "", false
	}
	id, ok := labels[ProjectSecretIDLabel]
	return id, ok
}

// GetSecretUseCaseFromLabels extracts and normalizes the use-case label value.
// The comparison is case-insensitive so "huggingface" and "HuggingFace" both
// resolve to the canonical "HuggingFace". Unrecognized values are passed through
// as-is to avoid dropping use cases that only exist on the API side.
func GetSecretUseCaseFromLabels(l map[string]string) *string {
	if l == nil {
		return nil
	}
	raw, ok := l[UseCaseLabel]
	if !ok || raw == "" {
		return nil
	}

	for _, candidate := range messaging.AllSecretUseCases {
		if strings.EqualFold(raw, string(candidate)) {
			s := string(candidate)
			return &s
		}
	}
	return &raw
}

// GetSecretScopeFromLabels extracts the secret scope from a labels map.
// The comparison is case-insensitive so both "Organization" and "organization" match.
// Returns nil if the scope label is not present or unrecognized.
func GetSecretScopeFromLabels(l map[string]string) *messaging.SecretScope {
	if l == nil {
		return nil
	}
	raw, ok := l[ProjectSecretScopeLabel]
	if !ok {
		return nil
	}

	for _, candidate := range messaging.AllSecretScopes {
		if strings.EqualFold(raw, string(candidate)) {
			return &candidate
		}
	}
	return nil
}

func PublishStatus(
	ctx context.Context,
	publisher messaging.MessagePublisher,
	projectSecretID string,
	scope *messaging.SecretScope,
	status messaging.ProjectSecretStatus,
	reason string,
) error {
	msg := &messaging.ProjectSecretsUpdateMessage{
		MessageType:     messaging.MessageTypeProjectSecretsUpdate,
		ProjectSecretID: projectSecretID,
		SecretScope:     scope,
		Status:          status,
		StatusReason:    &reason,
		UpdatedAt:       time.Now().UTC(),
	}
	return publisher.Publish(ctx, msg)
}

func HandleDeletion(
	ctx context.Context,
	c client.Client,
	publisher messaging.MessagePublisher,
	obj client.Object,
	finalizer string,
	deletionReason string,
) error {
	if !controllerutil.ContainsFinalizer(obj, finalizer) {
		return nil
	}

	labels := obj.GetLabels()
	if projectSecretID, ok := ExtractSecretID(labels); ok {
		scope := GetSecretScopeFromLabels(labels)
		if err := PublishStatus(ctx, publisher, projectSecretID, scope, messaging.ProjectSecretStatusDeleted, deletionReason); err != nil {
			return err
		}
	}

	return agent.RemoveFinalizer(ctx, c, obj, finalizer)
}
