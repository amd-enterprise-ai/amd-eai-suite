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
	"github.com/silogen/agent/internal/workloads/common"
)

// Reconciler reconciles ConfigMap objects for workload tracking.
// This controller handles ConfigMaps that are part of user workloads (labeled with workload-id).
// Storage ConfigMaps are handled by the storages/configmap controller.
type Reconciler struct {
	client.Client
	Publisher messaging.MessagePublisher
}

// Reconcile handles configmap events and publishes status updates.
func (r *Reconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := ctrl.LoggerFrom(ctx)

	var cm corev1.ConfigMap
	if err := r.Get(ctx, req.NamespacedName, &cm); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	if !cm.DeletionTimestamp.IsZero() {
		err := common.HandleDeletion(ctx, r.Client, r.Publisher, &cm)
		if err != nil {
			log.Error(err, "failed to handle deletion", "configmap", req.NamespacedName)
		}
		return ctrl.Result{}, err
	}

	componentData, err := common.ExtractComponentData(&cm)
	if err != nil {
		log.V(1).Info("skipping configmap without required labels",
			"configmap", cm.Name,
			"namespace", cm.Namespace,
			"error", err,
		)
		return ctrl.Result{}, nil
	}

	if err = agent.AddFinalizerIfNeeded(ctx, r.Client, &cm, common.WorkloadFinalizer); err != nil {
		log.Error(err, "failed to add finalizer", "configmap", req.NamespacedName)
		return ctrl.Result{}, err
	}

	status, statusReason := GetStatus(&cm)

	if err := common.PublishStatusMessage(ctx, r.Publisher, componentData, status, statusReason); err != nil {
		log.Error(err, "failed to publish configmap status")
		return ctrl.Result{}, err
	}

	log.Info("published configmap status",
		"configmap", cm.Name,
		"namespace", cm.Namespace,
		"status", status,
		"workload_id", componentData.WorkloadID,
		"component_id", componentData.ComponentID,
	)

	return ctrl.Result{}, nil
}

// SetupWithManager sets up the controller with the Manager.
func (r *Reconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		Named("workloads-config-map-controller").
		For(&corev1.ConfigMap{}).
		WithEventFilter(agent.ManagedNamespaceEventFilter(r.Client)).
		Complete(r)
}
