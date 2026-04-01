// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package pod

import (
	"context"
	"net/http"

	"github.com/go-logr/logr"
	admissionv1 "k8s.io/api/admission/v1"
	corev1 "k8s.io/api/core/v1"
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

	pod := &corev1.Pod{}
	if err := h.Decoder.Decode(req, pod); err != nil {
		return admission.Errored(http.StatusBadRequest, err)
	}

	common.EnsureKueueLabel(pod, req.Namespace)
	common.ApplyWorkloadTracking(pod, req, nsCtx)

	h.ensureKaiwoScheduler(&pod.Spec, req.Operation)

	return agent.CreatePatchResponse(req, pod, log)
}

// ensureKaiwoScheduler sets the pod scheduler to kaiwo when empty or default.
// We only run on Create because schedulerName is immutable on existing pods.
func (h *Webhook) ensureKaiwoScheduler(podSpec *corev1.PodSpec, operation admissionv1.Operation) {
	if operation != admissionv1.Create || podSpec == nil {
		return
	}
	if podSpec.SchedulerName != "" && podSpec.SchedulerName != defaultSchedulerName {
		return
	}
	podSpec.SchedulerName = kaiwoSchedulerName
}
