// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package externalsecret

import (
	"context"
	"encoding/json"
	"net/http"

	"github.com/go-logr/logr"
	common "github.com/silogen/agent/internal/common"
	secret "github.com/silogen/agent/internal/secrets/common"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
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

	nsCtx, err := common.GetProjectIdFromNamespace(ctx, h.Client, req.Namespace)
	if err != nil {
		log.Error(err, "failed to get namespace")
		return admission.Errored(http.StatusInternalServerError, err)
	}
	if nsCtx == nil {
		return admission.Allowed("namespace not managed by AIRM")
	}

	obj := &unstructured.Unstructured{}
	if err := json.Unmarshal(req.Object.Raw, &obj.Object); err != nil {
		return admission.Errored(http.StatusBadRequest, err)
	}

	secret.ApplySecretTracking(obj, req, nsCtx)

	return common.CreatePatchResponse(req, obj, log)
}
