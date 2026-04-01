// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package service

import (
	"context"

	agent "github.com/silogen/agent/internal/common"
	corev1 "k8s.io/api/core/v1"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"

	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/workloads/common"
)

// Reconciler reconciles Service objects for workload tracking.
type Reconciler struct {
	client.Client
	Publisher messaging.MessagePublisher
}

// Reconcile handles service events and publishes status updates.
func (r *Reconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := ctrl.LoggerFrom(ctx)

	var svc corev1.Service
	if err := r.Get(ctx, req.NamespacedName, &svc); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	if !svc.DeletionTimestamp.IsZero() {
		err := common.HandleDeletion(ctx, r.Client, r.Publisher, &svc)
		if err != nil {
			log.Error(err, "failed to handle deletion", "service", req.NamespacedName)
		}
		return ctrl.Result{}, err
	}

	componentData, err := common.ExtractComponentData(&svc)
	if err != nil {
		log.V(1).Info("skipping service without required labels",
			"service", svc.Name,
			"namespace", svc.Namespace,
			"error", err,
		)
		return ctrl.Result{}, nil
	}

	if err = agent.AddFinalizerIfNeeded(ctx, r.Client, &svc, common.WorkloadFinalizer); err != nil {
		log.Error(err, "failed to add finalizer", "service", req.NamespacedName)
		return ctrl.Result{}, err
	}

	status, statusReason := GetStatus(&svc)

	if err := common.PublishStatusMessage(ctx, r.Publisher, componentData, status, statusReason); err != nil {
		log.Error(err, "failed to publish service status")
		return ctrl.Result{}, err
	}

	log.Info("published service status",
		"service", svc.Name,
		"namespace", svc.Namespace,
		"status", status,
		"workload_id", componentData.WorkloadID,
		"component_id", componentData.ComponentID,
	)

	return ctrl.Result{}, nil
}

// SetupWithManager sets up the controller with the Manager.
func (r *Reconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&corev1.Service{}).
		WithEventFilter(agent.ManagedNamespaceEventFilter(r.Client)).
		Complete(r)
}
