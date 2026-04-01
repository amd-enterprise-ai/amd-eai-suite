// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package quotas

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/go-logr/logr"
	"github.com/silogen/agent/internal/messaging"
	kaiwov1alpha1 "github.com/silogen/kaiwo/apis/kaiwo/v1alpha1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
)

type QuotaHandler struct {
	clientset     kubernetes.Interface
	dynamicClient dynamic.Interface
	publisher     messaging.MessagePublisher
	logger        logr.Logger
}

func NewQuotaHandler(clientset kubernetes.Interface, dynamicClient dynamic.Interface, publisher messaging.MessagePublisher, logger logr.Logger) *QuotaHandler {
	return &QuotaHandler{
		clientset:     clientset,
		dynamicClient: dynamicClient,
		publisher:     publisher,
		logger:        logger,
	}
}

func (h *QuotaHandler) HandleCreate(_ context.Context, _ *messaging.RawMessage) error {
	return errors.New("create operation not supported")
}

func (h *QuotaHandler) HandleDelete(_ context.Context, _ *messaging.RawMessage) error {
	return errors.New("delete operation not supported")
}

func (h *QuotaHandler) HandleUpdate(ctx context.Context, msg *messaging.RawMessage) error {
	var allocationMsg messaging.ClusterQuotasAllocationMessage
	if err := json.Unmarshal(msg.Payload, &allocationMsg); err != nil {
		h.logger.Error(err, "failed to parse update message", "payload", string(msg.Payload))
		h.publishFailure(ctx, fmt.Sprintf("Failed to parse message: %v", err))
		return fmt.Errorf("failed to parse message: %w", err)
	}

	h.logger.Info("processing quota allocation",
		"quota_count", len(allocationMsg.QuotaAllocations),
		"priority_classes", len(allocationMsg.PriorityClasses),
	)

	desiredConfig := buildKaiwoQueueConfigManifest(&allocationMsg)

	gvr := schema.GroupVersionResource{
		Group:    kaiwov1alpha1.GroupVersion.Group,
		Version:  kaiwov1alpha1.GroupVersion.Version,
		Resource: KaiwoQueueConfigResource,
	}

	// Get existing to preserve resourceVersion
	existing, err := h.dynamicClient.Resource(gvr).Get(ctx, KaiwoQueueConfigDefaultName, metav1.GetOptions{})
	if err != nil {
		h.logger.Error(err, "failed to get kaiwo queue config")
		h.publishFailure(ctx, fmt.Sprintf("Failed to get KaiwoQueueConfig: %v", err))
		return fmt.Errorf("failed to get kaiwo queue config: %w", err)
	}

	desiredConfig.ResourceVersion = existing.GetResourceVersion()
	unstructuredMap, err := runtime.DefaultUnstructuredConverter.ToUnstructured(desiredConfig)
	if err != nil {
		h.logger.Error(err, "failed to convert to unstructured")
		h.publishFailure(ctx, fmt.Sprintf("Failed to convert to unstructured: %v", err))
		return fmt.Errorf("failed to convert to unstructured: %w", err)
	}

	_, err = h.dynamicClient.Resource(gvr).Update(ctx, &unstructured.Unstructured{Object: unstructuredMap}, metav1.UpdateOptions{})
	if err != nil {
		h.logger.Error(err, "failed to update kaiwo queue config")
		h.publishFailure(ctx, fmt.Sprintf("Failed to update KaiwoQueueConfig: %v", err))
		return fmt.Errorf("failed to update kaiwo queue config: %w", err)
	}

	h.logger.Info("kaiwo queue config updated",
		"name", KaiwoQueueConfigDefaultName,
		"cluster_queues", len(desiredConfig.Spec.ClusterQueues),
		"resource_flavors", len(desiredConfig.Spec.ResourceFlavors),
		"priority_classes", len(desiredConfig.Spec.WorkloadPriorityClasses),
	)

	return nil
}

// publishFailure sends a ClusterQuotaFailureMessage to the feedback queue.
func (h *QuotaHandler) publishFailure(ctx context.Context, reason string) {
	failureMsg := &messaging.ClusterQuotaFailureMessage{
		MessageType: messaging.MessageTypeClusterQuotasFailureMessage,
		UpdatedAt:   time.Now(),
		Reason:      reason,
	}

	if err := h.publisher.Publish(ctx, failureMsg); err != nil {
		h.logger.Error(err, "failed to publish failure message", "reason", reason)
	}
}
