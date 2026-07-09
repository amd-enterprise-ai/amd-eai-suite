// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package controller

import (
	"context"
	"fmt"

	"github.com/go-logr/logr"
	"github.com/silogen/ai-gateway-discovery/internal/aigateway"
	"github.com/silogen/ai-gateway-discovery/internal/common"
	"github.com/silogen/ai-gateway-discovery/internal/config"
	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime/schema"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

// InferenceServiceReconciler watches InferenceService objects and manages the
// corresponding InferencePool and AIGatewayRoute per IS.
// It uses a finalizer to ensure cleanup when an InferenceService is deleted.
type InferenceServiceReconciler struct {
	client.Client
	Config *config.ControllerConfig
	Log    logr.Logger
}

func (r *InferenceServiceReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := r.Log.WithValues("inferenceservice", req.NamespacedName)

	is := newInferenceService()
	if err := r.Get(ctx, req.NamespacedName, is); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	if !is.GetDeletionTimestamp().IsZero() {
		return r.handleDeletion(ctx, log, is)
	}

	modelName := r.resolveModelName(is)
	if modelName == "" {
		log.Info("skipping: model-name annotation absent", "annotation", r.Config.ModelNameAnnotation)
		return ctrl.Result{}, nil
	}

	if err := r.ensureFinalizer(ctx, is); err != nil {
		return ctrl.Result{}, err
	}

	entry := r.buildEntry(is, modelName)
	eppName := entry.ResourceName
	epp := aigateway.EPPRef{Name: eppName, Port: r.Config.EPPServicePort}

	if err := r.applyObj(ctx, aigateway.BuildInferencePool(entry, epp, r.Config.InferencePoolPort)); err != nil {
		log.Error(err, "failed to apply InferencePool", "name", entry.ResourceName)
		return ctrl.Result{}, err
	}

	if err := r.applyObj(ctx, aigateway.BuildEPPDeployment(entry, eppName, r.Config.EPPImage, r.Config.EPPServicePort)); err != nil {
		log.Error(err, "failed to apply EPP Deployment")
		return ctrl.Result{}, err
	}
	if err := r.applyObj(ctx, aigateway.BuildEPPService(entry, eppName, r.Config.EPPServicePort)); err != nil {
		log.Error(err, "failed to apply EPP Service")
		return ctrl.Result{}, err
	}

	if err := r.applyEPPRBAC(ctx, entry, eppName); err != nil {
		log.Error(err, "failed to apply EPP RBAC")
		return ctrl.Result{}, err
	}

	allowedGroup := is.GetAnnotations()[r.Config.AllowedGroupAnnotation]
	if err := r.applyObj(ctx, aigateway.BuildAIGatewayRoute(entry, r.Config, allowedGroup)); err != nil {
		log.Error(err, "failed to apply AIGatewayRoute", "name", entry.ResourceName)
		return ctrl.Result{}, err
	}

	log.Info("reconciled", "pool", entry.ResourceName, "model", entry.ModelName)
	return ctrl.Result{}, nil
}

func (r *InferenceServiceReconciler) handleDeletion(ctx context.Context, log logr.Logger, is *unstructured.Unstructured) (ctrl.Result, error) {
	finalizers := is.GetFinalizers()
	if !containsString(finalizers, common.Finalizer) {
		return ctrl.Result{}, nil
	}

	name := resourceName(is.GetNamespace(), is.GetName())
	if err := r.deleteGVK(ctx, aigateway.InferencePoolGVK, is.GetNamespace(), name); err != nil {
		log.Error(err, "failed to delete InferencePool", "name", name)
		return ctrl.Result{}, err
	}
	r.deleteGVK(ctx, aigateway.EPPDeploymentGVK, is.GetNamespace(), name) //nolint:errcheck
	r.deleteGVK(ctx, aigateway.EPPServiceGVK, is.GetNamespace(), name)    //nolint:errcheck
	r.deleteGVK(ctx, roleBindingGVK, is.GetNamespace(), name)             //nolint:errcheck
	r.deleteGVK(ctx, roleGVK, is.GetNamespace(), name)                    //nolint:errcheck

	is.SetFinalizers(removeString(finalizers, common.Finalizer))
	if err := r.Update(ctx, is); err != nil {
		return ctrl.Result{}, fmt.Errorf("removing finalizer: %w", err)
	}

	log.Info("cleaned up InferencePool and EPP resources", "name", name)
	return ctrl.Result{}, nil
}

func (r *InferenceServiceReconciler) ensureFinalizer(ctx context.Context, is *unstructured.Unstructured) error {
	finalizers := is.GetFinalizers()
	if containsString(finalizers, common.Finalizer) {
		return nil
	}
	is.SetFinalizers(append(finalizers, common.Finalizer))
	if err := r.Update(ctx, is); err != nil {
		return fmt.Errorf("adding finalizer: %w", err)
	}
	return nil
}

func (r *InferenceServiceReconciler) resolveModelName(is *unstructured.Unstructured) string {
	return is.GetAnnotations()[r.Config.ModelNameAnnotation]
}

func (r *InferenceServiceReconciler) buildEntry(is *unstructured.Unstructured, modelName string) aigateway.BackendEntry {
	return aigateway.BackendEntry{
		ResourceName: resourceName(is.GetNamespace(), is.GetName()),
		ISName:       is.GetName(),
		ISNamespace:  is.GetNamespace(),
		ISUID:        is.GetUID(),
		ModelName:    modelName,
		WorkloadID:   is.GetLabels()["airm.silogen.ai/workload-id"],
	}
}

var (
	roleGVK        = schema.GroupVersionKind{Group: "rbac.authorization.k8s.io", Version: "v1", Kind: "Role"}
	roleBindingGVK = schema.GroupVersionKind{Group: "rbac.authorization.k8s.io", Version: "v1", Kind: "RoleBinding"}
)

// applyEPPRBAC creates a Role and RoleBinding in the IS namespace granting the
// default ServiceAccount (used by inference-epp) the permissions it needs to
// watch InferencePools, Pods, and InferenceModelRewrites.
func (r *InferenceServiceReconciler) applyEPPRBAC(ctx context.Context, entry aigateway.BackendEntry, eppName string) error {
	role := &unstructured.Unstructured{}
	role.SetGroupVersionKind(roleGVK)
	role.SetName(eppName)
	role.SetNamespace(entry.ISNamespace)
	_ = unstructured.SetNestedSlice(role.Object, []interface{}{
		map[string]interface{}{
			"apiGroups": []interface{}{""},
			"resources": []interface{}{"pods"},
			"verbs":     []interface{}{"get", "list", "watch"},
		},
		map[string]interface{}{
			"apiGroups": []interface{}{"inference.networking.k8s.io"},
			"resources": []interface{}{"inferencepools"},
			"verbs":     []interface{}{"get", "list", "watch"},
		},
		map[string]interface{}{
			"apiGroups": []interface{}{"inference.networking.x-k8s.io"},
			"resources": []interface{}{"inferencemodelrewrites", "inferenceobjectives"},
			"verbs":     []interface{}{"get", "list", "watch"},
		},
	}, "rules")
	if err := r.applyObj(ctx, role); err != nil {
		return fmt.Errorf("applying EPP Role: %w", err)
	}

	rb := &unstructured.Unstructured{}
	rb.SetGroupVersionKind(roleBindingGVK)
	rb.SetName(eppName)
	rb.SetNamespace(entry.ISNamespace)
	_ = unstructured.SetNestedSlice(rb.Object, []interface{}{
		map[string]interface{}{
			"kind":      "ServiceAccount",
			"name":      "default",
			"namespace": entry.ISNamespace,
		},
	}, "subjects")
	_ = unstructured.SetNestedMap(rb.Object, map[string]interface{}{
		"apiGroup": "rbac.authorization.k8s.io",
		"kind":     "Role",
		"name":     eppName,
	}, "roleRef")
	return r.applyObj(ctx, rb)
}

func (r *InferenceServiceReconciler) applyObj(ctx context.Context, obj *unstructured.Unstructured) error {
	return r.Patch(ctx, obj, client.Apply, client.FieldOwner(common.FieldManager), client.ForceOwnership)
}

func (r *InferenceServiceReconciler) deleteGVK(ctx context.Context, gvk schema.GroupVersionKind, namespace, name string) error {
	obj := &unstructured.Unstructured{}
	obj.SetGroupVersionKind(gvk)
	obj.SetNamespace(namespace)
	obj.SetName(name)
	err := r.Delete(ctx, obj)
	if errors.IsNotFound(err) {
		return nil
	}
	return err
}

func (r *InferenceServiceReconciler) SetupWithManager(mgr ctrl.Manager) error {
	is := newInferenceService()
	return ctrl.NewControllerManagedBy(mgr).
		For(is).
		WithEventFilter(hasManagedLabel(r.Config.ManagedLabelName, r.Config.ManagedLabelValue)).
		Complete(r)
}

// newInferenceService returns an unstructured object set up for KServe InferenceService.
func newInferenceService() *unstructured.Unstructured {
	obj := &unstructured.Unstructured{}
	obj.SetGroupVersionKind(aigateway.InferenceServiceGVK)
	return obj
}

func containsString(slice []string, s string) bool {
	for _, v := range slice {
		if v == s {
			return true
		}
	}
	return false
}

func removeString(slice []string, s string) []string {
	out := make([]string, 0, len(slice))
	for _, v := range slice {
		if v != s {
			out = append(out, v)
		}
	}
	return out
}
