// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package aimservice

import (
	"context"
	"fmt"
	"net/http"

	aimv1alpha1 "github.com/amd-enterprise-ai/aim-engine/api/v1alpha1"
	aimv1alpha2 "github.com/amd-enterprise-ai/aim-engine/api/v1alpha2"
	"github.com/go-logr/logr"
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

	// AIM Engine uses None conversion strategy, so admission requests arrive
	// in whatever apiVersion the client sent. Decode into the matching kind.
	var aimService client.Object
	switch req.Kind.Version {
	case "v1alpha2":
		aimService = &aimv1alpha2.AIMService{}
	case "v1alpha1":
		aimService = &aimv1alpha1.AIMService{}
	default:
		return admission.Errored(http.StatusBadRequest,
			fmt.Errorf("unsupported AIMService apiVersion %q", req.Kind.Group+"/"+req.Kind.Version))
	}
	if err := h.Decoder.Decode(req, aimService); err != nil {
		return admission.Errored(http.StatusBadRequest, err)
	}

	common.ApplyWorkloadTracking(aimService, req, nsCtx)

	return agent.CreatePatchResponse(req, aimService, log)
}
