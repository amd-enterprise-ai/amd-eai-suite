// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package pod

import (
	"context"

	agent "github.com/silogen/agent/internal/common"
	corev1 "k8s.io/api/core/v1"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"

	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/workloads/common"
)

// Reconciler reconciles Pod objects for workload tracking.
type Reconciler struct {
	client.Client
	Publisher messaging.MessagePublisher
}

// Reconcile handles pod events and publishes status updates.
//
// Note: Pods use finalizers conditionally - only for pods with workload-id labels (tracked by AIRM).
// This ensures reliable deletion tracking for standalone pods while avoiding overhead for untracked pods.
// Child pods (from Deployments/Jobs) get finalizers if tracked, but parent resource tracking is also in place.
func (r *Reconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := ctrl.LoggerFrom(ctx)

	var pod corev1.Pod
	if err := r.Get(ctx, req.NamespacedName, &pod); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	if !pod.DeletionTimestamp.IsZero() {
		err := common.HandleDeletion(ctx, r.Client, r.Publisher, &pod)
		if err != nil {
			log.Error(err, "failed to handle deletion", "pod", req.NamespacedName)
		}
		return ctrl.Result{}, err
	}

	componentData, err := common.ExtractComponentData(&pod)
	if err != nil {
		log.V(1).Info("skipping pod without required labels",
			"pod", pod.Name,
			"namespace", pod.Namespace,
			"error", err,
		)
		return ctrl.Result{}, nil
	}

	if err = agent.AddFinalizerIfNeeded(ctx, r.Client, &pod, common.WorkloadFinalizer); err != nil {
		log.Error(err, "failed to add finalizer", "pod", req.NamespacedName)
		return ctrl.Result{}, err
	}

	// Publish auto-discovery message if this is an auto-discovered workload
	if componentData.AutoDiscovered {
		if err := common.PublishAutoDiscoveryMessage(ctx, r.Publisher, componentData); err != nil {
			log.Error(err, "failed to publish auto-discovery message")
			return ctrl.Result{}, err
		}
		log.Info("published auto-discovery message",
			"pod", pod.Name,
			"namespace", pod.Namespace,
			"workload_id", componentData.WorkloadID,
			"component_id", componentData.ComponentID,
			"submitter", componentData.Submitter,
		)
	}

	status, statusReason := GetStatus(&pod)

	if err := common.PublishStatusMessage(ctx, r.Publisher, componentData, status, statusReason); err != nil {
		log.Error(err, "failed to publish pod status")
		return ctrl.Result{}, err
	}

	log.Info("published pod status",
		"pod", pod.Name,
		"namespace", pod.Namespace,
		"status", status,
		"workload_id", componentData.WorkloadID,
		"component_id", componentData.ComponentID,
	)

	return ctrl.Result{}, nil
}

// SetupWithManager sets up the controller with the Manager.
func (r *Reconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&corev1.Pod{}).
		WithEventFilter(agent.ManagedNamespaceEventFilter(r.Client)).
		Complete(r)
}
