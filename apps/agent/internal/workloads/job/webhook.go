// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package job

import (
	"context"
	"net/http"

	"github.com/go-logr/logr"
	batchv1 "k8s.io/api/batch/v1"
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

	job := &batchv1.Job{}
	if err := h.Decoder.Decode(req, job); err != nil {
		return admission.Errored(http.StatusBadRequest, err)
	}

	common.EnsureKueueLabel(job, req.Namespace)
	common.ApplyWorkloadTracking(job, req, nsCtx)
	job.Spec.Template.Labels = common.PropagateTrackingLabelsToTemplate(job, job.Spec.Template.Labels)

	return agent.CreatePatchResponse(req, job, log)
}
