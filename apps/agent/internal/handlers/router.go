// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package handlers

import (
	"context"

	"github.com/go-logr/logr"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"

	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/namespaces"
	"github.com/silogen/agent/internal/quotas"
	"github.com/silogen/agent/internal/secrets"
	"github.com/silogen/agent/internal/storages/configmap"
	"github.com/silogen/agent/internal/workloads"
)

// Router routes messages to the appropriate handler.
type Router struct {
	logger    logr.Logger
	namespace ResourceHandler
	quota     ResourceHandler
	secret    ResourceHandler
	configmap ResourceHandler
	workload  ResourceHandler
}

// NewRouter creates a new Router with all handlers.
func NewRouter(clientset kubernetes.Interface, dynamicClient dynamic.Interface, publisher messaging.MessagePublisher, logger logr.Logger) *Router {
	return &Router{
		logger:    logger,
		namespace: namespaces.NewNamespaceHandler(clientset, publisher, logger),
		quota:     quotas.NewQuotaHandler(clientset, dynamicClient, publisher, logger),
		secret:    secrets.NewSecretHandler(clientset, dynamicClient, publisher, logger),
		configmap: configmap.NewConfigMapHandler(clientset, publisher, logger),
		workload:  workloads.NewWorkloadHandler(clientset, dynamicClient, publisher, logger),
	}
}

// Handle routes a message to the appropriate handler.
func (r *Router) Handle(ctx context.Context, msg *messaging.RawMessage) error {
	switch msg.Type {
	case messaging.MessageTypeProjectNamespaceCreate:
		return r.namespace.HandleCreate(ctx, msg)

	case messaging.MessageTypeProjectNamespaceDelete:
		return r.namespace.HandleDelete(ctx, msg)

	case messaging.MessageTypeClusterQuotasAllocationMessage:
		return r.quota.HandleUpdate(ctx, msg)

	case messaging.MessageTypeProjectSecretsCreate:
		return r.secret.HandleCreate(ctx, msg)

	case messaging.MessageTypeProjectSecretsDelete:
		return r.secret.HandleDelete(ctx, msg)

	case messaging.MessageTypeProjectS3StorageCreate:
		return r.configmap.HandleCreate(ctx, msg)

	case messaging.MessageTypeProjectStorageDelete:
		return r.configmap.HandleDelete(ctx, msg)

	case messaging.MessageTypeWorkload:
		return r.workload.HandleCreate(ctx, msg)

	case messaging.MessageTypeDeleteWorkload:
		return r.workload.HandleDelete(ctx, msg)

	default:
		r.logger.Info("WARN: unknown message type", "type", msg.Type)
		return nil
	}
}
