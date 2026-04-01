// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package quotas

import (
	"context"

	agent "github.com/silogen/agent/internal/common"
	"github.com/silogen/agent/internal/messaging"
	kaiwov1alpha1 "github.com/silogen/kaiwo/apis/kaiwo/v1alpha1"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

// KaiwoQueueConfigReconciler reconciles KaiwoQueueConfig objects.
type KaiwoQueueConfigReconciler struct {
	client.Client
	Publisher messaging.MessagePublisher
}

// Reconcile handles KaiwoQueueConfig events and publishes status updates.
func (r *KaiwoQueueConfigReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := ctrl.LoggerFrom(ctx)
	var config kaiwov1alpha1.KaiwoQueueConfig
	if err := r.Get(ctx, req.NamespacedName, &config); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	if !config.DeletionTimestamp.IsZero() {
		err := HandleDeletion(ctx, r.Client, r.Publisher, &config)
		if err != nil {
			log.Error(err, "failed to handle deletion", "kaiwoqueueconfig", req.NamespacedName)
		}
		return ctrl.Result{}, err
	}

	if err := agent.AddFinalizerIfNeeded(ctx, r.Client, &config, kaiwoQueueConfigFinalizer); err != nil {
		return ctrl.Result{}, err
	}

	if config.Status.Status == kaiwov1alpha1.QueueConfigStatusFailed {
		if err := publishQuotasFailureMessage(ctx, r.Publisher, &config); err != nil {
			log.Error(err, "failed to publish quotas failure message")
			return ctrl.Result{}, err
		}
		return ctrl.Result{}, nil
	}

	if err := publishStatusUpdate(ctx, r.Publisher, &config); err != nil {
		log.Error(err, "failed to publish status")
		return ctrl.Result{}, err
	}

	return ctrl.Result{}, nil
}

// SetupWithManager sets up the controller with the Manager.
func (r *KaiwoQueueConfigReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&kaiwov1alpha1.KaiwoQueueConfig{}).
		Complete(r)
}
