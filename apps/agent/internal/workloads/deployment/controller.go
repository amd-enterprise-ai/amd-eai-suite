// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package deployment

import (
	"context"

	agent "github.com/silogen/agent/internal/common"
	appsv1 "k8s.io/api/apps/v1"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"

	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/workloads/common"
)

// Reconciler reconciles Deployment objects for workload tracking.
type Reconciler struct {
	client.Client
	Publisher messaging.MessagePublisher
}

// Reconcile handles deployment events and publishes status updates.
func (r *Reconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := ctrl.LoggerFrom(ctx)

	var deployment appsv1.Deployment
	if err := r.Get(ctx, req.NamespacedName, &deployment); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	if !deployment.DeletionTimestamp.IsZero() {
		err := common.HandleDeletion(ctx, r.Client, r.Publisher, &deployment)
		if err != nil {
			log.Error(err, "failed to handle deletion", "deployment", req.NamespacedName)
		}
		return ctrl.Result{}, err
	}

	if err := agent.AddFinalizerIfNeeded(ctx, r.Client, &deployment, common.WorkloadFinalizer); err != nil {
		log.Error(err, "failed to add finalizer", "deployment", req.NamespacedName)
		return ctrl.Result{}, err
	}

	componentData, err := common.ExtractComponentData(&deployment)
	if err != nil {
		log.V(1).Info("skipping deployment without required labels",
			"deployment", deployment.Name,
			"namespace", deployment.Namespace,
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
			"deployment", deployment.Name,
			"namespace", deployment.Namespace,
			"workload_id", componentData.WorkloadID,
			"component_id", componentData.ComponentID,
			"submitter", componentData.Submitter,
		)
	}

	status, statusReason := GetStatus(&deployment)

	if err := common.PublishStatusMessage(ctx, r.Publisher, componentData, status, statusReason); err != nil {
		log.Error(err, "failed to publish deployment status")
		return ctrl.Result{}, err
	}

	log.Info("published deployment status",
		"deployment", deployment.Name,
		"namespace", deployment.Namespace,
		"status", status,
		"workload_id", componentData.WorkloadID,
		"component_id", componentData.ComponentID,
	)

	return ctrl.Result{}, nil
}

// SetupWithManager sets up the controller with the Manager.
func (r *Reconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&appsv1.Deployment{}).
		WithEventFilter(agent.ManagedNamespaceEventFilter(r.Client)).
		Complete(r)
}
