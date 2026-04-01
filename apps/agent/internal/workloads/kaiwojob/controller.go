// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package kaiwojob

import (
	"context"

	agent "github.com/silogen/agent/internal/common"
	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/workloads/common"
	kaiwov1alpha1 "github.com/silogen/kaiwo/apis/kaiwo/v1alpha1"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

// Reconciler reconciles KaiwoJob objects for workload tracking.
type Reconciler struct {
	client.Client
	Publisher messaging.MessagePublisher
}

// Reconcile handles kaiwojob events and publishes status updates.
func (r *Reconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := ctrl.LoggerFrom(ctx)

	var kaiwoJob kaiwov1alpha1.KaiwoJob
	if err := r.Get(ctx, req.NamespacedName, &kaiwoJob); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	if !kaiwoJob.DeletionTimestamp.IsZero() {
		err := common.HandleDeletion(ctx, r.Client, r.Publisher, &kaiwoJob)
		if err != nil {
			log.Error(err, "failed to handle deletion", "kaiwojob", req.NamespacedName)
		}
		return ctrl.Result{}, err
	}

	if err := agent.AddFinalizerIfNeeded(ctx, r.Client, &kaiwoJob, common.WorkloadFinalizer); err != nil {
		log.Error(err, "failed to add finalizer", "kaiwojob", req.NamespacedName)
		return ctrl.Result{}, err
	}

	componentData, err := common.ExtractComponentData(&kaiwoJob)
	if err != nil {
		log.V(1).Info("skipping kaiwojob without required labels",
			"kaiwojob", kaiwoJob.Name,
			"namespace", kaiwoJob.Namespace,
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
			"kaiwojob", kaiwoJob.Name,
			"namespace", kaiwoJob.Namespace,
			"workload_id", componentData.WorkloadID,
			"component_id", componentData.ComponentID,
			"submitter", componentData.Submitter,
		)
	}

	status, statusReason := GetStatus(&kaiwoJob)
	if status == "" {
		return ctrl.Result{}, nil
	}

	if err := common.PublishStatusMessage(ctx, r.Publisher, componentData, status, statusReason); err != nil {
		log.Error(err, "failed to publish kaiwojob status")
		return ctrl.Result{}, err
	}

	log.Info(
		"published kaiwojob status",
		"kaiwojob", kaiwoJob.Name,
		"namespace", kaiwoJob.Namespace,
		"workload_id", componentData.WorkloadID,
		"component_id", componentData.ComponentID,
		"status", status,
	)

	return ctrl.Result{}, nil
}

// SetupWithManager sets up the controller with the Manager.
func (r *Reconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&kaiwov1alpha1.KaiwoJob{}).
		WithEventFilter(agent.ManagedNamespaceEventFilter(r.Client)).
		Complete(r)
}
