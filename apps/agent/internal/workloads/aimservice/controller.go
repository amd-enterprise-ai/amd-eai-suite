// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package aimservice

import (
	"context"

	aimv1alpha1 "github.com/amd-enterprise-ai/aim-engine/api/v1alpha1"
	agent "github.com/silogen/agent/internal/common"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"

	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/workloads/common"
)

// Reconciler reconciles AIMService objects for workload tracking.
type Reconciler struct {
	client.Client
	Publisher messaging.MessagePublisher
}

// Reconcile handles aimservice events and publishes status updates.
func (r *Reconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := ctrl.LoggerFrom(ctx)

	var aimService aimv1alpha1.AIMService
	if err := r.Get(ctx, req.NamespacedName, &aimService); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	if !aimService.DeletionTimestamp.IsZero() {
		err := common.HandleDeletion(ctx, r.Client, r.Publisher, &aimService)
		if err != nil {
			log.Error(err, "failed to handle deletion", "aimservice", req.NamespacedName)
		}
		return ctrl.Result{}, err
	}

	if err := agent.AddFinalizerIfNeeded(ctx, r.Client, &aimService, common.WorkloadFinalizer); err != nil {
		log.Error(err, "failed to add finalizer", "aimservice", req.NamespacedName)
		return ctrl.Result{}, err
	}

	componentData, err := common.ExtractComponentData(&aimService)
	if err != nil {
		log.V(1).Info("skipping aimservice without required labels",
			"aimservice", aimService.Name,
			"namespace", aimService.Namespace,
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
			"aimservice", aimService.Name,
			"namespace", aimService.Namespace,
			"workload_id", componentData.WorkloadID,
			"component_id", componentData.ComponentID,
			"submitter", componentData.Submitter,
		)
	}

	status, statusReason := GetStatus(&aimService)
	if status == "" {
		log.V(1).Info("skipping status publish for aimservice with no status",
			"aimservice", aimService.Name,
			"namespace", aimService.Namespace,
			"reason", statusReason,
		)
		return ctrl.Result{}, nil
	}

	if err := common.PublishStatusMessage(ctx, r.Publisher, componentData, status, statusReason); err != nil {
		log.Error(err, "failed to publish aimservice status")
		return ctrl.Result{}, err
	}

	log.Info(
		"published aimservice status",
		"aimservice", aimService.Name,
		"namespace", aimService.Namespace,
		"workload_id", componentData.WorkloadID,
		"component_id", componentData.ComponentID,
		"status", status,
	)

	return ctrl.Result{}, nil
}

// SetupWithManager sets up the controller with the Manager.
func (r *Reconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&aimv1alpha1.AIMService{}).
		WithEventFilter(agent.ManagedNamespaceEventFilter(r.Client)).
		Complete(r)
}
