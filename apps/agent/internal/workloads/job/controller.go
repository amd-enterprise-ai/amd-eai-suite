// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package job

import (
	"context"

	agent "github.com/silogen/agent/internal/common"
	batchv1 "k8s.io/api/batch/v1"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"

	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/workloads/common"
)

// Reconciler reconciles Job objects for workload tracking.
type Reconciler struct {
	client.Client
	Publisher messaging.MessagePublisher
}

// Reconcile handles job events and publishes status updates.
func (r *Reconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := ctrl.LoggerFrom(ctx)

	var job batchv1.Job
	if err := r.Get(ctx, req.NamespacedName, &job); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	if !job.DeletionTimestamp.IsZero() {
		err := common.HandleDeletion(ctx, r.Client, r.Publisher, &job)
		if err != nil {
			log.Error(err, "failed to handle deletion", "job", req.NamespacedName)
		}
		return ctrl.Result{}, err
	}

	if err := agent.AddFinalizerIfNeeded(ctx, r.Client, &job, common.WorkloadFinalizer); err != nil {
		log.Error(err, "failed to add finalizer", "job", req.NamespacedName)
		return ctrl.Result{}, err
	}

	componentData, err := common.ExtractComponentData(&job)
	if err != nil {
		log.V(1).Info("skipping job without required labels",
			"job", job.Name,
			"namespace", job.Namespace,
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
			"job", job.Name,
			"namespace", job.Namespace,
			"workload_id", componentData.WorkloadID,
			"component_id", componentData.ComponentID,
			"submitter", componentData.Submitter,
		)
	}

	status, statusReason := GetStatus(&job)

	if err := common.PublishStatusMessage(ctx, r.Publisher, componentData, status, statusReason); err != nil {
		log.Error(err, "failed to publish job status")
		return ctrl.Result{}, err
	}

	log.Info("published job status",
		"job", job.Name,
		"namespace", job.Namespace,
		"workload_id", componentData.WorkloadID,
		"component_id", componentData.ComponentID,
		"status", status,
	)

	return ctrl.Result{}, nil
}

// SetupWithManager sets up the controller with the Manager.
func (r *Reconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&batchv1.Job{}).
		WithEventFilter(agent.ManagedNamespaceEventFilter(r.Client)).
		Complete(r)
}
