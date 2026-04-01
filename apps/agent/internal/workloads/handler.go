// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package workloads

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"

	"github.com/go-logr/logr"
	"github.com/google/uuid"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	"k8s.io/client-go/discovery/cached/memory"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/restmapper"

	"github.com/silogen/agent/internal/messaging"
	common "github.com/silogen/agent/internal/workloads/common"
)

type Handler struct {
	clientset     kubernetes.Interface
	dynamicClient dynamic.Interface
	publisher     messaging.MessagePublisher
	logger        logr.Logger
	mapper        apimeta.RESTMapper
}

func NewWorkloadHandler(clientset kubernetes.Interface, dynamicClient dynamic.Interface, publisher messaging.MessagePublisher, logger logr.Logger) *Handler {
	memCache := memory.NewMemCacheClient(clientset.Discovery())
	return &Handler{
		clientset:     clientset,
		dynamicClient: dynamicClient,
		publisher:     publisher,
		logger:        logger.WithName("workloads-handler"),
		mapper:        restmapper.NewDeferredDiscoveryRESTMapper(memCache),
	}
}

func (h *Handler) HandleCreate(ctx context.Context, msg *messaging.RawMessage) error {
	var createMsg messaging.WorkloadMessage
	if err := json.Unmarshal(msg.Payload, &createMsg); err != nil {
		return fmt.Errorf("failed to parse WorkloadMessage: %w", err)
	}

	if createMsg.Manifest == "" {
		return fmt.Errorf("workload manifest is required")
	}
	if createMsg.WorkloadID == "" {
		return fmt.Errorf("workload_id is required")
	}
	if _, err := uuid.Parse(createMsg.WorkloadID); err != nil {
		return fmt.Errorf("invalid workload_id: %w", err)
	}

	objs, err := common.DecodeYAMLDocuments(createMsg.Manifest)
	if err != nil {
		return fmt.Errorf("failed to parse workload manifest: %w", err)
	}

	for _, obj := range objs {
		if applyErr := common.ApplyObject(ctx, h.dynamicClient, h.mapper, obj); applyErr != nil {
			h.logger.Error(applyErr, "failed to apply workload object",
				"apiVersion", obj.GetAPIVersion(),
				"kind", obj.GetKind(),
				"namespace", obj.GetNamespace(),
				"name", obj.GetName(),
			)

			componentData, dataErr := common.ExtractComponentData(obj)
			if dataErr != nil {
				h.logger.Error(dataErr, "failed to extract component data for status publish",
					"apiVersion", obj.GetAPIVersion(),
					"kind", obj.GetKind(),
					"namespace", obj.GetNamespace(),
					"name", obj.GetName(),
				)
				continue
			}

			if pubErr := common.PublishStatusMessage(ctx, h.publisher, componentData, "CreateFailed", applyErr.Error()); pubErr != nil {
				h.logger.Error(pubErr, "failed to publish component status",
					"apiVersion", obj.GetAPIVersion(),
					"kind", obj.GetKind(),
					"namespace", obj.GetNamespace(),
					"name", obj.GetName(),
				)
			}
		}
	}

	return nil
}

func (h *Handler) HandleDelete(ctx context.Context, msg *messaging.RawMessage) error {
	deleteMsg, err := common.ParseDeleteWorkloadMessage(msg)
	if err != nil {
		return err
	}

	labelSelector := common.WorkloadIDLabelSelector(deleteMsg.WorkloadID)
	deletedCount := DeleteKnownWorkloadComponents(
		ctx,
		h.dynamicClient,
		h.mapper,
		h.publisher,
		labelSelector,
	)
	if deletedCount > 0 {
		return nil
	}

	reason := fmt.Sprintf("No resources found for deletion: %s", labelSelector)
	if pubErr := common.PublishWorkloadStatus(
		ctx,
		h.publisher,
		deleteMsg.WorkloadID,
		messaging.WorkloadStatusDeleted,
		reason,
	); pubErr != nil {
		h.logger.Error(pubErr, "failed to publish workload deleted status", "workload_id", deleteMsg.WorkloadID)
	}
	return nil
}

func (h *Handler) HandleUpdate(ctx context.Context, msg *messaging.RawMessage) error {
	return errors.New("update operation not supported")
}
