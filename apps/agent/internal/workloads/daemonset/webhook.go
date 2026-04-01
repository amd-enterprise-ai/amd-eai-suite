// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package daemonset

import (
	"context"
	"net/http"

	"github.com/go-logr/logr"
	appsv1 "k8s.io/api/apps/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/webhook/admission"

	agent "github.com/silogen/agent/internal/common"
	"github.com/silogen/agent/internal/workloads/common"
)

type Webhook struct {
	Client  client.Client
	Decoder admission.Decoder
	Logger  logr.Logger
}

func (h *Webhook) Handle(ctx context.Context, req admission.Request) admission.Response {
	log := h.Logger.WithValues("namespace", req.Namespace, "name", req.Name)

	nsCtx, err := agent.GetProjectIdFromNamespace(ctx, h.Client, req.Namespace)
	if err != nil {
		log.Error(err, "failed to get namespace")
		return admission.Errored(http.StatusInternalServerError, err)
	}
	if nsCtx == nil {
		return admission.Allowed("namespace not managed by AIRM")
	}

	daemonSet := &appsv1.DaemonSet{}
	if err := h.Decoder.Decode(req, daemonSet); err != nil {
		return admission.Errored(http.StatusBadRequest, err)
	}

	common.EnsureKueueLabel(daemonSet, req.Namespace)
	common.ApplyWorkloadTracking(daemonSet, req, nsCtx)
	daemonSet.Spec.Template.Labels = common.PropagateTrackingLabelsToTemplate(daemonSet, daemonSet.Spec.Template.Labels)

	return agent.CreatePatchResponse(req, daemonSet, log)
}
