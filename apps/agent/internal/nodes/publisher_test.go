// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package nodes

import (
	"context"
	"errors"
	"testing"

	"github.com/silogen/agent/internal/kubernetes"
	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/testutils"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes/fake"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"
)

func createTestNode(name string, cpuCores string, memoryGi string) *corev1.Node {
	return &corev1.Node{
		ObjectMeta: metav1.ObjectMeta{
			Name: name,
		},
		Status: corev1.NodeStatus{
			Allocatable: corev1.ResourceList{
				corev1.ResourceCPU:              resource.MustParse(cpuCores),
				corev1.ResourceMemory:           resource.MustParse(memoryGi),
				corev1.ResourceEphemeralStorage: resource.MustParse("100Gi"),
			},
			Conditions: []corev1.NodeCondition{
				{
					Type:   corev1.NodeReady,
					Status: corev1.ConditionTrue,
				},
			},
		},
	}
}

func TestSendClusterNodes_Success(t *testing.T) {
	node1 := createTestNode("node-1", "4", "16Gi")
	node2 := createTestNode("node-2", "8", "32Gi")

	fakeClientset := fake.NewSimpleClientset()
	_, _ = fakeClientset.CoreV1().Nodes().Create(context.Background(), node1, metav1.CreateOptions{})
	_, _ = fakeClientset.CoreV1().Nodes().Create(context.Background(), node2, metav1.CreateOptions{})

	k8sClient := &kubernetes.Client{
		Clientset: fakeClientset,
	}
	mockPublisher := testutils.NewMockPublisher()
	logger := zap.New()
	ctx := context.Background()

	err := PublishClusterNodes(ctx, mockPublisher, k8sClient, logger)

	require.NoError(t, err)
	require.Len(t, mockPublisher.Published, 1)

	msg, ok := mockPublisher.Published[0].(*messaging.ClusterNodesMessage)
	require.True(t, ok, "message should be of type *ClusterNodesMessage")

	assert.Equal(t, messaging.MessageTypeClusterNodes, msg.MessageType)
	assert.Len(t, msg.ClusterNodes, 2)
	assert.NotZero(t, msg.UpdatedAt)

	// Verify node details
	assert.Equal(t, "node-1", msg.ClusterNodes[0].Name)
	assert.Equal(t, "node-2", msg.ClusterNodes[1].Name)

	// Verify CPU/Memory in milliCores and bytes
	assert.Equal(t, int64(4000), msg.ClusterNodes[0].CPUMilliCores)
	assert.Equal(t, int64(8000), msg.ClusterNodes[1].CPUMilliCores)
}

func TestSendClusterNodes_NoNodes(t *testing.T) {
	fakeClientset := fake.NewSimpleClientset()
	k8sClient := &kubernetes.Client{
		Clientset: fakeClientset,
	}
	mockPublisher := testutils.NewMockPublisher()
	logger := zap.New()
	ctx := context.Background()

	err := PublishClusterNodes(ctx, mockPublisher, k8sClient, logger)

	require.NoError(t, err)
	require.Len(t, mockPublisher.Published, 1)

	msg, ok := mockPublisher.Published[0].(*messaging.ClusterNodesMessage)
	require.True(t, ok)
	assert.Empty(t, msg.ClusterNodes)
}

func TestSendClusterNodes_PublishError(t *testing.T) {
	node := createTestNode("node-1", "4", "16Gi")

	fakeClientset := fake.NewSimpleClientset()
	_, _ = fakeClientset.CoreV1().Nodes().Create(context.Background(), node, metav1.CreateOptions{})

	k8sClient := &kubernetes.Client{
		Clientset: fakeClientset,
	}

	mockPublisher := testutils.NewMockFailingPublisher(errors.New("publish failed"))
	logger := zap.New()
	ctx := context.Background()

	err := PublishClusterNodes(ctx, mockPublisher, k8sClient, logger)

	require.Error(t, err)
	assert.Contains(t, err.Error(), "failed to publish cluster nodes")
}
