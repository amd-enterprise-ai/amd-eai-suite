// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package daemonset

import (
	"context"

	agent "github.com/silogen/agent/internal/common"
	appsv1 "k8s.io/api/apps/v1"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"

	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/workloads/common"
)

// Reconciler reconciles DaemonSet objects for workload tracking.
type Reconciler struct {
	client.Client
	Publisher messaging.MessagePublisher
}

// Reconcile handles daemonset events and publishes status updates.
func (r *Reconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := ctrl.LoggerFrom(ctx)

	var daemonSet appsv1.DaemonSet
	if err := r.Get(ctx, req.NamespacedName, &daemonSet); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	if !daemonSet.DeletionTimestamp.IsZero() {
		err := common.HandleDeletion(ctx, r.Client, r.Publisher, &daemonSet)
		if err != nil {
			log.Error(err, "failed to handle deletion", "daemonset", req.NamespacedName)
		}
		return ctrl.Result{}, err
	}

	if err := agent.AddFinalizerIfNeeded(ctx, r.Client, &daemonSet, common.WorkloadFinalizer); err != nil {
		log.Error(err, "failed to add finalizer", "daemonset", req.NamespacedName)
		return ctrl.Result{}, err
	}

	componentData, err := common.ExtractComponentData(&daemonSet)
	if err != nil {
		log.V(1).Info("skipping daemonset without required labels",
			"daemonset", daemonSet.Name,
			"namespace", daemonSet.Namespace,
			"error", err,
		)
		return ctrl.Result{}, nil
	}

	// Publish auto-discovery message if this is an auto-discovered workload
	if componentData.AutoDiscovered {
		if err := common.PublishAutoDiscoveryMessage(ctx, r.Publisher, componentData); err != nil {
			log.Error(err, "failed to publish auto-discovery message")
			return ctrl.Result{}, err
		}
		log.Info("published auto-discovery message",
			"daemonset", daemonSet.Name,
			"namespace", daemonSet.Namespace,
			"workload_id", componentData.WorkloadID,
			"component_id", componentData.ComponentID,
			"submitter", componentData.Submitter,
		)
	}

	status, statusReason := GetStatus(&daemonSet)

	if err := common.PublishStatusMessage(ctx, r.Publisher, componentData, status, statusReason); err != nil {
		log.Error(err, "failed to publish daemonset status")
		return ctrl.Result{}, err
	}

	log.Info("published daemonset status",
		"daemonset", daemonSet.Name,
		"namespace", daemonSet.Namespace,
		"status", status,
		"workload_id", componentData.WorkloadID,
		"component_id", componentData.ComponentID,
	)

	return ctrl.Result{}, nil
}

// SetupWithManager sets up the controller with the Manager.
func (r *Reconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&appsv1.DaemonSet{}).
		WithEventFilter(agent.ManagedNamespaceEventFilter(r.Client)).
		Complete(r)
}
