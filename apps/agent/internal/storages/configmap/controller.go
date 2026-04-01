// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package configmap

import (
	"context"

	agent "github.com/silogen/agent/internal/common"
	corev1 "k8s.io/api/core/v1"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"

	"github.com/silogen/agent/internal/messaging"
)

// ConfigMapReconciler reconciles ConfigMap objects.
type ConfigMapReconciler struct {
	client.Client
	Publisher messaging.MessagePublisher
}

// Reconcile handles ConfigMap events and publishes status updates.
func (r *ConfigMapReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := ctrl.LoggerFrom(ctx)

	var cm corev1.ConfigMap
	if err := r.Get(ctx, req.NamespacedName, &cm); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	// Only process ConfigMaps with the project-storage-id label
	storageID, hasLabel := cm.Labels[ProjectStorageIDLabel]
	if !hasLabel {
		return ctrl.Result{}, nil
	}

	if !cm.DeletionTimestamp.IsZero() {
		err := HandleDeletion(ctx, r.Client, r.Publisher, &cm)
		if err != nil {
			log.Error(err, "failed to handle deletion", "configmap", req.NamespacedName)
		}
		return ctrl.Result{}, err
	}

	// Add finalizer if not present
	if err := agent.AddFinalizerIfNeeded(ctx, r.Client, &cm, ConfigMapFinalizer); err != nil {
		return ctrl.Result{}, err
	}

	// Publish status update
	if err := publishStorageStatus(ctx, r.Publisher, storageID, messaging.ConfigMapStatusAdded, "ConfigMap is ready."); err != nil {
		log.Error(err, "failed to publish status")
		return ctrl.Result{}, err
	}

	log.Info("published configmap status",
		"configmap", cm.Name,
		"namespace", cm.Namespace,
		"storage_id", storageID,
		"status", messaging.ConfigMapStatusAdded,
	)

	return ctrl.Result{}, nil
}

// SetupWithManager sets up the controller with the Manager.
func (r *ConfigMapReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&corev1.ConfigMap{}).
		WithEventFilter(agent.ManagedNamespaceEventFilter(r.Client)).
		Complete(r)
}
