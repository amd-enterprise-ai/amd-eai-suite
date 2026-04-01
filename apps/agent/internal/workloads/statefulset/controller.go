// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package statefulset

import (
	"context"

	agent "github.com/silogen/agent/internal/common"
	appsv1 "k8s.io/api/apps/v1"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"

	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/workloads/common"
)

// Reconciler reconciles StatefulSet objects for workload tracking.
type Reconciler struct {
	client.Client
	Publisher messaging.MessagePublisher
}

// Reconcile handles statefulset events and publishes status updates.
func (r *Reconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := ctrl.LoggerFrom(ctx)

	var statefulSet appsv1.StatefulSet
	if err := r.Get(ctx, req.NamespacedName, &statefulSet); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	if !statefulSet.DeletionTimestamp.IsZero() {
		err := common.HandleDeletion(ctx, r.Client, r.Publisher, &statefulSet)
		if err != nil {
			log.Error(err, "failed to handle deletion", "statefulset", req.NamespacedName)
		}
		return ctrl.Result{}, err
	}

	if err := agent.AddFinalizerIfNeeded(ctx, r.Client, &statefulSet, common.WorkloadFinalizer); err != nil {
		log.Error(err, "failed to add finalizer", "statefulset", req.NamespacedName)
		return ctrl.Result{}, err
	}

	componentData, err := common.ExtractComponentData(&statefulSet)
	if err != nil {
		log.V(1).Info("skipping statefulset without required labels",
			"statefulset", statefulSet.Name,
			"namespace", statefulSet.Namespace,
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
			"statefulset", statefulSet.Name,
			"namespace", statefulSet.Namespace,
			"workload_id", componentData.WorkloadID,
			"component_id", componentData.ComponentID,
			"submitter", componentData.Submitter,
		)
	}

	status, statusReason := GetStatus(&statefulSet)
	if status == "" {
		return ctrl.Result{}, nil
	}

	if err := common.PublishStatusMessage(ctx, r.Publisher, componentData, status, statusReason); err != nil {
		log.Error(err, "failed to publish statefulset status")
		return ctrl.Result{}, err
	}

	log.Info("published statefulset status",
		"statefulset", statefulSet.Name,
		"namespace", statefulSet.Namespace,
		"workload_id", componentData.WorkloadID,
		"component_id", componentData.ComponentID,
		"status", status,
	)

	return ctrl.Result{}, nil
}

// SetupWithManager sets up the controller with the Manager.
func (r *Reconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&appsv1.StatefulSet{}).
		WithEventFilter(agent.ManagedNamespaceEventFilter(r.Client)).
		Complete(r)
}
