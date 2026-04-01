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
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
)

func extractProjectIDFromNamespace(ns *corev1.Namespace) string {
	if ns == nil || ns.Labels == nil {
		return ""
	}
	return ns.Labels[agent.ProjectIDLabel]
}

// mapK8sPhaseToNamespaceStatus maps Kubernetes namespace phase to NamespaceStatus.
func mapK8sPhaseToNamespaceStatus(phase string) messaging.NamespaceStatus {
	if phase == "" {
		return messaging.NamespaceStatusFailed
	}

	switch phase {
	case "Active":
		return messaging.NamespaceStatusActive
	case "Terminating":
		return messaging.NamespaceStatusTerminating
	case "Pending":
		return messaging.NamespaceStatusPending
	default:
		return messaging.NamespaceStatusFailed
	}
}

// BuildNamespaceManifest creates a Kubernetes namespace manifest with required labels.
func BuildNamespaceManifest(name, projectID string) *corev1.Namespace {
	return &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name: name,
			Labels: map[string]string{
				agent.ProjectIDLabel: projectID,
				KueueManagedLabel:    "true",
			},
		},
	}
}

// GetNamespaceStatusReason returns a human-readable reason for the namespace status.
func GetNamespaceStatusReason(status messaging.NamespaceStatus) string {
	switch status {
	case messaging.NamespaceStatusDeleted:
		return "Namespace has been deleted"
	case messaging.NamespaceStatusActive:
		return "Namespace is active"
	case messaging.NamespaceStatusTerminating:
		return "Namespace is terminating"
	case messaging.NamespaceStatusPending:
		return "Namespace is pending"
	case messaging.NamespaceStatusDeleteFailed:
		return "Namespace deletion failed"
	case messaging.NamespaceStatusFailed:
		return "Unknown namespace phase: Unknown"
	default:
		return "Unknown namespace status"
	}
}

// HandleDeletion publishes a terminating status and removes the namespace finalizer.
//
// The caller must check that the object is being deleted before calling this function.
// If publishing fails, it returns the publish error and leaves the finalizer in place so the controller will retry.
func HandleDeletion(
	ctx context.Context,
	c client.Client,
	publisher messaging.MessagePublisher,
	obj client.Object,
) error {
	if !controllerutil.ContainsFinalizer(obj, namespaceFinalizer) {
		return nil
	}

	projectID := ""
	if labels := obj.GetLabels(); labels != nil {
		projectID = labels[agent.ProjectIDLabel]
	}

	if err := publishNamespaceStatus(ctx, publisher, obj.GetName(), projectID, messaging.NamespaceStatusTerminating); err != nil {
		return err
	}

	return agent.RemoveFinalizer(ctx, c, obj, namespaceFinalizer)
}

func publishNamespaceStatus(
	ctx context.Context,
	publisher messaging.MessagePublisher,
	namespaceName, projectID string,
	status messaging.NamespaceStatus,
) error {
	log := ctrl.LoggerFrom(ctx)
	if projectID == "" {
		msg := &messaging.UnmanagedNamespaceMessage{
			MessageType:     messaging.MessageTypeUnmanagedNamespace,
			NamespaceName:   namespaceName,
			NamespaceStatus: status,
		}
		if err := publisher.Publish(ctx, msg); err != nil {
			return err
		}
		log.Info("published unmanaged namespace status",
			"namespace", namespaceName,
			"status", status,
		)
		return nil
	}

	reason := GetNamespaceStatusReason(status)
	msg := &messaging.ProjectNamespaceStatusMessage{
		MessageType:  messaging.MessageTypeProjectNamespaceStatus,
		ProjectID:    projectID,
		Status:       status,
		StatusReason: &reason,
	}
	if err := publisher.Publish(ctx, msg); err != nil {
		return err
	}
	log.Info("published namespace status",
		"namespace", namespaceName,
		"project_id", projectID,
		"status", status,
	)
	return nil
}

func handleDeleted(ctx context.Context, publisher messaging.MessagePublisher, namespaceName string) (ctrl.Result, error) {
	log := ctrl.LoggerFrom(ctx)

	log.Info("namespace completely deleted from cluster", "namespace", namespaceName)
	if err := publishNamespaceDeletedMessage(ctx, publisher, namespaceName); err != nil {
		log.Error(err, "failed to publish deletion status")
		return ctrl.Result{}, err
	}

	log.Info("namespace deletion status published successfully", "namespace", namespaceName)
	return ctrl.Result{}, nil
}

func publishNamespaceDeletedMessage(ctx context.Context, publisher messaging.MessagePublisher, namespaceName string) error {
	log := ctrl.LoggerFrom(ctx)

	msg := &messaging.NamespaceDeletedMessage{
		MessageType:   messaging.MessageTypeNamespaceDeleted,
		NamespaceName: namespaceName,
	}
	if err := publisher.Publish(ctx, msg); err != nil {
		return err
	}
	log.Info("published namespace deletion by name",
		"namespace", namespaceName,
	)
	return nil
}

func ensureRoleBinding(ctx context.Context, c client.Client, ns *corev1.Namespace) (bool, error) {
	rbName := "project-member-role-binding"
	rb := &rbacv1.RoleBinding{}
	err := c.Get(ctx, client.ObjectKey{Namespace: ns.Name, Name: rbName}, rb)

	if err == nil {
		return false, nil
	}

	if !errors.IsNotFound(err) {
		return false, err
	}

	rb = &rbacv1.RoleBinding{
		ObjectMeta: metav1.ObjectMeta{
			Name:      rbName,
			Namespace: ns.Name,
			OwnerReferences: []metav1.OwnerReference{{
				APIVersion: "v1",
				Kind:       "Namespace",
				Name:       ns.Name,
				UID:        ns.UID,
			}},
		},
		RoleRef: rbacv1.RoleRef{
			APIGroup: "rbac.authorization.k8s.io",
			Kind:     "ClusterRole",
			Name:     "airm-project-member",
		},
		Subjects: []rbacv1.Subject{
			// Backwards compatibility, since the prefix was previously 'oidc'
			{
				Kind:     "Group",
				Name:     "oidc" + ns.Name,
				APIGroup: "rbac.authorization.k8s.io",
			},
			// The kubernetes cluster applies an OIDC prefix of 'oidc:', so we adjust the group to expect that
			{
				Kind:     "Group",
				Name:     "oidc:" + ns.Name,
				APIGroup: "rbac.authorization.k8s.io",
			},
		},
	}

	if err := c.Create(ctx, rb); err != nil {
		if errors.IsAlreadyExists(err) {
			return false, nil
		}
		return false, err
	}
	return true, nil
}
