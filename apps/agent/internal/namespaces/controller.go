// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package namespaces

import (
	"context"

	agent "github.com/silogen/agent/internal/common"
	"github.com/silogen/agent/internal/messaging"
	corev1 "k8s.io/api/core/v1"
	rbacv1 "k8s.io/api/rbac/v1"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

// NamespaceReconciler reconciles Namespace objects.
type NamespaceReconciler struct {
	client.Client
	Publisher messaging.MessagePublisher
}

// Reconcile handles namespace events and publishes status updates.
func (r *NamespaceReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := ctrl.LoggerFrom(ctx)

	var ns corev1.Namespace
	if err := r.Get(ctx, client.ObjectKey{Name: req.Name}, &ns); err != nil {
		if client.IgnoreNotFound(err) == nil {
			return handleDeleted(ctx, r.Publisher, req.Name)
		}
		return ctrl.Result{}, err
	}

	projectID := extractProjectIDFromNamespace(&ns)

	if !ns.DeletionTimestamp.IsZero() {
		err := HandleDeletion(ctx, r.Client, r.Publisher, &ns)
		if err != nil {
			log.Error(err, "failed to handle deletion", "namespace", req.Name)
		}
		return ctrl.Result{}, err
	}

	if err := agent.AddFinalizerIfNeeded(ctx, r.Client, &ns, namespaceFinalizer); err != nil {
		return ctrl.Result{}, err
	}

	phase := string(ns.Status.Phase)
	status := mapK8sPhaseToNamespaceStatus(phase)

	if err := publishNamespaceStatus(ctx, r.Publisher, ns.Name, projectID, status); err != nil {
		log.Error(err, "failed to publish status")
		return ctrl.Result{}, err
	}

	if projectID != "" {
		created, err := ensureRoleBinding(ctx, r.Client, &ns)
		if err != nil {
			log.Error(err, "failed to ensure rolebinding")
			return ctrl.Result{}, err
		}
		if created {
			log.Info("created rolebinding", "namespace", ns.Name)
		}
	}

	return ctrl.Result{}, nil
}

func (r *NamespaceReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&corev1.Namespace{}).
		Owns(&rbacv1.RoleBinding{}).
		Complete(r)
}
