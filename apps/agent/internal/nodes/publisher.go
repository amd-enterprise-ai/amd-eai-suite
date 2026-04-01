// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package nodes

import (
	"context"
	"fmt"
	"time"

	"github.com/go-logr/logr"
	"github.com/silogen/agent/internal/kubernetes"
	"github.com/silogen/agent/internal/messaging"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// PublishClusterNodes retrieves cluster nodes and publishes them to the messaging system.
func PublishClusterNodes(
	ctx context.Context,
	publisher messaging.MessagePublisher,
	k8sClient *kubernetes.Client,
	logger logr.Logger,
) error {
	nodes, err := k8sClient.Clientset.CoreV1().Nodes().List(ctx, metav1.ListOptions{})
	if err != nil {
		return fmt.Errorf("failed to retrieve cluster nodes: %w", err)
	}

	clusterNodes := make([]messaging.ClusterNode, 0, len(nodes.Items))
	for _, node := range nodes.Items {
		clusterNode := mapNodeToClusterNode(&node)
		clusterNodes = append(clusterNodes, clusterNode)
	}

	message := &messaging.ClusterNodesMessage{
		MessageType:  messaging.MessageTypeClusterNodes,
		ClusterNodes: clusterNodes,
		UpdatedAt:    time.Now().UTC(),
	}

	if err := publisher.Publish(ctx, message); err != nil {
		logger.Error(err, "failed to publish cluster nodes")
		return fmt.Errorf("failed to publish cluster nodes: %w", err)
	}

	logger.Info("cluster nodes sent successfully", "cluster_nodes", len(clusterNodes))
	return nil
}
