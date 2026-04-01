// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package nodes

import (
	"context"
	"time"

	"github.com/silogen/agent/internal/messaging"
	corev1 "k8s.io/api/core/v1"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

// NodeReconciler reconciles Node objects.
type NodeReconciler struct {
	client.Client
	Publisher messaging.MessagePublisher
}

// Reconcile handles node events and publishes updates.
func (r *NodeReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	var node corev1.Node
	if err := r.Get(ctx, client.ObjectKey{Name: req.Name}, &node); err != nil {
		if client.IgnoreNotFound(err) == nil {
			return r.handleDeletion(ctx, req.Name)
		}
		return ctrl.Result{}, err
	}

	// Check if node is being deleted
	if !node.DeletionTimestamp.IsZero() {
		return r.handleDeletion(ctx, node.Name)
	}

	// Node was created or updated
	return r.handleUpdate(ctx, &node)
}

func (r *NodeReconciler) handleUpdate(ctx context.Context, node *corev1.Node) (ctrl.Result, error) {
	log := ctrl.LoggerFrom(ctx)

	log.Info("node update detected", "node", node.Name)

	clusterNode := mapNodeToClusterNode(node)

	// Create update message
	msg := &messaging.ClusterNodeUpdateMessage{
		MessageType: messaging.MessageTypeClusterNodeUpdate,
		ClusterNode: clusterNode,
		UpdatedAt:   time.Now(),
	}

	// Publish message
	if err := r.Publisher.Publish(ctx, msg); err != nil {
		log.Error(err, "failed to publish node update", "node", node.Name)
		return ctrl.Result{}, err
	}

	log.Info("published node update",
		"node", node.Name,
		"cpu_milli_cores", clusterNode.CPUMilliCores,
		"memory_bytes", clusterNode.MemoryBytes,
		"status", clusterNode.Status,
		"is_ready", clusterNode.IsReady,
	)

	return ctrl.Result{}, nil
}

func (r *NodeReconciler) handleDeletion(ctx context.Context, nodeName string) (ctrl.Result, error) {
	log := ctrl.LoggerFrom(ctx)

	log.Info("node deletion detected", "node", nodeName)

	// Create delete message
	msg := &messaging.ClusterNodeDeleteMessage{
		MessageType: messaging.MessageTypeClusterNodeDelete,
		Name:        nodeName,
		UpdatedAt:   time.Now(),
	}

	// Publish message
	if err := r.Publisher.Publish(ctx, msg); err != nil {
		log.Error(err, "failed to publish node deletion, will retry", "node", nodeName)
		return ctrl.Result{}, err
	}

	log.Info("published node deletion", "node", nodeName)
	return ctrl.Result{}, nil
}

// SetupWithManager sets up the controller with the Manager.
func (r *NodeReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&corev1.Node{}).
		Complete(r)
}
