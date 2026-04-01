// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package kaiwojob

import (
	"context"
	"net/http"

	"github.com/go-logr/logr"
	kaiwov1alpha1 "github.com/silogen/kaiwo/apis/kaiwo/v1alpha1"
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

	kaiwoJob := &kaiwov1alpha1.KaiwoJob{}
	if err := h.Decoder.Decode(req, kaiwoJob); err != nil {
		return admission.Errored(http.StatusBadRequest, err)
	}

	if kaiwoJob.Spec.ClusterQueue == "" {
		kaiwoJob.Spec.ClusterQueue = req.Namespace
	}

	common.ApplyWorkloadTracking(kaiwoJob, req, nsCtx)

	return agent.CreatePatchResponse(req, kaiwoJob, log)
}
