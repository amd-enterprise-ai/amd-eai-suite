// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package k8ssecret

import (
	"context"

	agent "github.com/silogen/agent/internal/common"
	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/secrets/common"
	corev1 "k8s.io/api/core/v1"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

type KubernetesSecretReconciler struct {
	client.Client
	Publisher messaging.MessagePublisher
}

func (r *KubernetesSecretReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := ctrl.LoggerFrom(ctx)

	var secret corev1.Secret
	if err := r.Get(ctx, req.NamespacedName, &secret); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	projectSecretID, hasLabel := common.ExtractSecretID(secret.Labels)

	if !secret.DeletionTimestamp.IsZero() {
		err := common.HandleDeletion(ctx, r.Client, r.Publisher, &secret, Finalizer, "Secret deleted successfully")
		if err != nil {
			log.Error(err, "failed to handle deletion", "secret", req.NamespacedName)
		}
		return ctrl.Result{}, err
	}

	if !hasLabel {
		return ctrl.Result{}, nil
	}

	if err := agent.AddFinalizerIfNeeded(ctx, r.Client, &secret, Finalizer); err != nil {
		return ctrl.Result{}, err
	}

	secretData, err := common.ExtractSecretData(&secret, messaging.SecretKindKubernetesSecret)
	if err != nil {
		log.V(1).Info("skipping secret, cannot extract data", "error", err)
		return ctrl.Result{}, nil
	}

	if secretData.AutoDiscovered {
		if err := common.PublishAutoDiscoveryMessage(ctx, r.Publisher, secretData); err != nil {
			log.Error(err, "failed to publish auto-discovery message")
			return ctrl.Result{}, err
		}
		log.Info("published auto-discovery message",
			"secret", secret.Name,
			"namespace", secret.Namespace,
			"project_secret_id", projectSecretID,
		)
	}

	status := messaging.ProjectSecretStatusSynced

	if err := common.PublishStatus(ctx, r.Publisher, projectSecretID, secretData.Scope, status, common.ProjectSecretStatusReadyReason); err != nil {
		log.Error(err, "failed to publish status")
		return ctrl.Result{}, err
	}

	log.Info("secret reconciled successfully",
		"secret", secret.Name,
		"namespace", secret.Namespace,
		"project_secret_id", projectSecretID,
	)
	return ctrl.Result{}, nil
}

func (r *KubernetesSecretReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&corev1.Secret{}).
		WithEventFilter(agent.ManagedNamespaceEventFilter(r.Client)).
		Complete(r)
}
