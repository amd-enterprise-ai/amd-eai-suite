// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package ingress

import (
	"context"

	agent "github.com/silogen/agent/internal/common"
	networkingv1 "k8s.io/api/networking/v1"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"

	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/workloads/common"
)

// Reconciler reconciles Ingress objects for workload tracking.
type Reconciler struct {
	client.Client
	Publisher messaging.MessagePublisher
}

// Reconcile handles ingress events and publishes status updates.
func (r *Reconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := ctrl.LoggerFrom(ctx)

	var ing networkingv1.Ingress
	if err := r.Get(ctx, req.NamespacedName, &ing); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	if !ing.DeletionTimestamp.IsZero() {
		err := common.HandleDeletion(ctx, r.Client, r.Publisher, &ing)
		if err != nil {
			log.Error(err, "failed to handle deletion", "ingress", req.NamespacedName)
		}
		return ctrl.Result{}, err
	}

	componentData, err := common.ExtractComponentData(&ing)
	if err != nil {
		log.V(1).Info("skipping ingress without required labels",
			"ingress", ing.Name,
			"namespace", ing.Namespace,
			"error", err,
		)
		return ctrl.Result{}, nil
	}

	if err = agent.AddFinalizerIfNeeded(ctx, r.Client, &ing, common.WorkloadFinalizer); err != nil {
		log.Error(err, "failed to add finalizer", "ingress", req.NamespacedName)
		return ctrl.Result{}, err
	}

	status, statusReason := GetStatus(&ing)

	if err := common.PublishStatusMessage(ctx, r.Publisher, componentData, status, statusReason); err != nil {
		log.Error(err, "failed to publish ingress status")
		return ctrl.Result{}, err
	}

	log.Info("published ingress status",
		"ingress", ing.Name,
		"namespace", ing.Namespace,
		"status", status,
		"workload_id", componentData.WorkloadID,
		"component_id", componentData.ComponentID,
	)

	return ctrl.Result{}, nil
}

// SetupWithManager sets up the controller with the Manager.
func (r *Reconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&networkingv1.Ingress{}).
		WithEventFilter(agent.ManagedNamespaceEventFilter(r.Client)).
		Complete(r)
}
