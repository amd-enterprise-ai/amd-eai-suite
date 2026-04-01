// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package k8ssecret

import (
	"context"
	"net/http"

	"github.com/go-logr/logr"
	agent "github.com/silogen/agent/internal/common"
	secretcommon "github.com/silogen/agent/internal/secrets/common"
	corev1 "k8s.io/api/core/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/webhook/admission"
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

	secret := &corev1.Secret{}
	if err := h.Decoder.Decode(req, secret); err != nil {
		return admission.Errored(http.StatusBadRequest, err)
	}

	secretcommon.ApplySecretTracking(secret, req, nsCtx)

	return agent.CreatePatchResponse(req, secret, log)
}
