// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package externalsecret

import (
	"context"
	"fmt"

	agent "github.com/silogen/agent/internal/common"
	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/secrets/common"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime/schema"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

type ExternalSecretReconciler struct {
	client.Client
	Publisher messaging.MessagePublisher
	GVK       schema.GroupVersionKind
}

func (r *ExternalSecretReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := ctrl.LoggerFrom(ctx)

	if r.GVK.Empty() {
		return ctrl.Result{}, fmt.Errorf("external secret controller GVK is not set")
	}

	externalSecretObj := &unstructured.Unstructured{}
	externalSecretObj.SetGroupVersionKind(r.GVK)
	if err := r.Get(ctx, req.NamespacedName, externalSecretObj); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	lbls := externalSecretObj.GetLabels()
	if lbls == nil {
		lbls = make(map[string]string)
	}

	projectSecretID, hasLabel := common.ExtractSecretID(lbls)

	if !externalSecretObj.GetDeletionTimestamp().IsZero() {
		err := common.HandleDeletion(ctx, r.Client, r.Publisher, externalSecretObj, Finalizer, "ExternalSecret deleted successfully")
		if err != nil {
			log.Error(err, "failed to handle deletion", "externalsecret", req.NamespacedName)
		}
		return ctrl.Result{}, err
	}

	if !hasLabel {
		return ctrl.Result{}, nil
	}

	if err := agent.AddFinalizerIfNeeded(ctx, r.Client, externalSecretObj, Finalizer); err != nil {
		return ctrl.Result{}, err
	}

	secretData, err := common.ExtractSecretData(externalSecretObj, messaging.SecretKindExternalSecret)
	if err != nil {
		log.V(1).Info("skipping external secret, cannot extract data", "error", err)
		return ctrl.Result{}, nil
	}

	if secretData.AutoDiscovered {
		if err := common.PublishAutoDiscoveryMessage(ctx, r.Publisher, secretData); err != nil {
			log.Error(err, "failed to publish auto-discovery message")
			return ctrl.Result{}, err
		}
		log.Info("published auto-discovery message",
			"name", externalSecretObj.GetName(),
			"namespace", externalSecretObj.GetNamespace(),
			"project_secret_id", projectSecretID,
		)
	}

	// Extract status from ExternalSecret conditions
	status, statusReason := GetExternalSecretStatus(externalSecretObj)

	if status == "" {
		return ctrl.Result{}, nil
	}

	if err := common.PublishStatus(ctx, r.Publisher, projectSecretID, secretData.Scope, status, statusReason); err != nil {
		log.Error(err, "failed to publish status")
		return ctrl.Result{}, err
	}

	log.Info("external secret reconciled successfully",
		"name", externalSecretObj.GetName(),
		"namespace", externalSecretObj.GetNamespace(),
		"project_secret_id", projectSecretID,
		"status", status,
	)
	return ctrl.Result{}, nil
}

func (r *ExternalSecretReconciler) SetupWithManager(mgr ctrl.Manager) error {
	if r.GVK.Empty() {
		return fmt.Errorf("external secret controller GVK is not set")
	}

	obj := &unstructured.Unstructured{}
	obj.SetGroupVersionKind(r.GVK)

	return ctrl.NewControllerManagedBy(mgr).
		For(obj).
		WithEventFilter(agent.ManagedNamespaceEventFilter(r.Client)).
		Complete(r)
}
