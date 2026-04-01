// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package kaiwoservice

import (
	"context"

	agent "github.com/silogen/agent/internal/common"
	kaiwov1alpha1 "github.com/silogen/kaiwo/apis/kaiwo/v1alpha1"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"

	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/workloads/common"
)

// Reconciler reconciles KaiwoService objects for workload tracking.
type Reconciler struct {
	client.Client
	Publisher messaging.MessagePublisher
}

// Reconcile handles kaiwoservice events and publishes status updates.
func (r *Reconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := ctrl.LoggerFrom(ctx)

	var kaiwoService kaiwov1alpha1.KaiwoService
	if err := r.Get(ctx, req.NamespacedName, &kaiwoService); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	if !kaiwoService.DeletionTimestamp.IsZero() {
		err := common.HandleDeletion(ctx, r.Client, r.Publisher, &kaiwoService)
		if err != nil {
			log.Error(err, "failed to handle deletion", "kaiwoservice", req.NamespacedName)
		}
		return ctrl.Result{}, err
	}

	if err := agent.AddFinalizerIfNeeded(ctx, r.Client, &kaiwoService, common.WorkloadFinalizer); err != nil {
		log.Error(err, "failed to add finalizer", "kaiwoservice", req.NamespacedName)
		return ctrl.Result{}, err
	}

	componentData, err := common.ExtractComponentData(&kaiwoService)
	if err != nil {
		log.V(1).Info("skipping kaiwoservice without required labels",
			"kaiwoservice", kaiwoService.Name,
			"namespace", kaiwoService.Namespace,
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
			"kaiwoservice", kaiwoService.Name,
			"namespace", kaiwoService.Namespace,
			"workload_id", componentData.WorkloadID,
			"component_id", componentData.ComponentID,
			"submitter", componentData.Submitter,
		)
	}

	status, statusReason := GetStatus(&kaiwoService)
	if status == "" {
		return ctrl.Result{}, nil
	}

	if err := common.PublishStatusMessage(ctx, r.Publisher, componentData, status, statusReason); err != nil {
		log.Error(err, "failed to publish kaiwoservice status")
		return ctrl.Result{}, err
	}

	log.Info(
		"published kaiwoservice status",
		"kaiwoservice", kaiwoService.Name,
		"namespace", kaiwoService.Namespace,
		"workload_id", componentData.WorkloadID,
		"component_id", componentData.ComponentID,
		"status", status,
	)

	return ctrl.Result{}, nil
}

// SetupWithManager sets up the controller with the Manager.
func (r *Reconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&kaiwov1alpha1.KaiwoService{}).
		WithEventFilter(agent.ManagedNamespaceEventFilter(r.Client)).
		Complete(r)
}
