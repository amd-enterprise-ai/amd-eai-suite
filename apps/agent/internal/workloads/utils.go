// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package workloads

import (
	"context"

	"github.com/silogen/agent/internal/messaging"
	common "github.com/silogen/agent/internal/workloads/common"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/dynamic"
)

// DeleteKnownWorkloadComponents best-effort deletes workload components matching the label selector.
//
// - It skips resource kinds that are not installed/discoverable (REST mapping fails).
// - It only deletes namespaced resources.
// - It publishes a "DeleteFailed" component status message if a deletion call fails (excluding NotFound).
func DeleteKnownWorkloadComponents(
	ctx context.Context,
	dynamicClient dynamic.Interface,
	mapper apimeta.RESTMapper,
	publisher messaging.MessagePublisher,
	labelSelector string,
) int {
	deletedCount := 0

	for _, gk := range KnownComponentGroupKinds {
		mapping, err := mapper.RESTMapping(gk, "")
		if err != nil {
			continue
		}
		if mapping.Scope.Name() != apimeta.RESTScopeNameNamespace {
			continue
		}

		res := dynamicClient.Resource(mapping.Resource)
		list, err := res.List(ctx, metav1.ListOptions{LabelSelector: labelSelector})
		if err != nil || len(list.Items) == 0 {
			continue
		}

		for i := range list.Items {
			item := &list.Items[i]
			ns := item.GetNamespace()
			name := item.GetName()

			deletedCount++
			propagationPolicy := metav1.DeletePropagationForeground
			delErr := res.Namespace(ns).Delete(ctx, name, metav1.DeleteOptions{
				PropagationPolicy: &propagationPolicy,
			})
			if delErr != nil && !apierrors.IsNotFound(delErr) {
				componentData, err := common.ExtractComponentData(item)
				if err != nil {
					continue
				}

				if pubErr := common.PublishStatusMessage(ctx, publisher, componentData, "DeleteFailed", delErr.Error()); pubErr != nil {
					_ = pubErr
				}
			}
		}
	}

	return deletedCount
}
