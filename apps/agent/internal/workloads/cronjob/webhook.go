// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package cronjob

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

	cronJob := &batchv1.CronJob{}
	if err := h.Decoder.Decode(req, cronJob); err != nil {
		return admission.Errored(http.StatusBadRequest, err)
	}

	if cronJob.Spec.JobTemplate.Labels == nil {
		cronJob.Spec.JobTemplate.Labels = make(map[string]string)
	}
	cronJob.Spec.JobTemplate.Labels[common.KueueNameLabel] = req.Namespace

	common.ApplyWorkloadTracking(cronJob, req, nsCtx)

	cronJob.Spec.JobTemplate.Labels = common.PropagateTrackingLabelsToTemplate(cronJob, cronJob.Spec.JobTemplate.Labels)
	cronJob.Spec.JobTemplate.Spec.Template.Labels = common.PropagateTrackingLabelsToTemplate(cronJob, cronJob.Spec.JobTemplate.Spec.Template.Labels)

	return agent.CreatePatchResponse(req, cronJob, log)
}
