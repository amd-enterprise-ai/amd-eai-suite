// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package workloads

import (
	"github.com/go-logr/logr"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/webhook/admission"

	"github.com/silogen/agent/internal/workloads/aimservice"
	"github.com/silogen/agent/internal/workloads/cronjob"
	"github.com/silogen/agent/internal/workloads/daemonset"
	"github.com/silogen/agent/internal/workloads/deployment"
	"github.com/silogen/agent/internal/workloads/job"
	"github.com/silogen/agent/internal/workloads/kaiwojob"
	"github.com/silogen/agent/internal/workloads/kaiwoservice"
	"github.com/silogen/agent/internal/workloads/pod"
	"github.com/silogen/agent/internal/workloads/replicaset"
	"github.com/silogen/agent/internal/workloads/statefulset"
)

func SetupWebhooks(mgr ctrl.Manager, logger logr.Logger) error {
	decoder := admission.NewDecoder(mgr.GetScheme())
	client := mgr.GetClient()

	mgr.GetWebhookServer().Register("/mutate-pod", &admission.Webhook{
		Handler: &pod.Webhook{Client: client, Decoder: decoder, Logger: logger.WithName("pod-webhook")},
	})
	mgr.GetWebhookServer().Register("/mutate-deployment", &admission.Webhook{
		Handler: &deployment.Webhook{Client: client, Decoder: decoder, Logger: logger.WithName("deployment-webhook")},
	})
	mgr.GetWebhookServer().Register("/mutate-statefulset", &admission.Webhook{
		Handler: &statefulset.Webhook{Client: client, Decoder: decoder, Logger: logger.WithName("statefulset-webhook")},
	})
	mgr.GetWebhookServer().Register("/mutate-daemonset", &admission.Webhook{
		Handler: &daemonset.Webhook{Client: client, Decoder: decoder, Logger: logger.WithName("daemonset-webhook")},
	})
	mgr.GetWebhookServer().Register("/mutate-replicaset", &admission.Webhook{
		Handler: &replicaset.Webhook{Client: client, Decoder: decoder, Logger: logger.WithName("replicaset-webhook")},
	})
	mgr.GetWebhookServer().Register("/mutate-job", &admission.Webhook{
		Handler: &job.Webhook{Client: client, Decoder: decoder, Logger: logger.WithName("job-webhook")},
	})
	mgr.GetWebhookServer().Register("/mutate-cronjob", &admission.Webhook{
		Handler: &cronjob.Webhook{Client: client, Decoder: decoder, Logger: logger.WithName("cronjob-webhook")},
	})
	mgr.GetWebhookServer().Register("/mutate-kaiwojob", &admission.Webhook{
		Handler: &kaiwojob.Webhook{Client: client, Decoder: decoder, Logger: logger.WithName("kaiwojob-webhook")},
	})
	mgr.GetWebhookServer().Register("/mutate-kaiwoservice", &admission.Webhook{
		Handler: &kaiwoservice.Webhook{Client: client, Decoder: decoder, Logger: logger.WithName("kaiwoservice-webhook")},
	})
	mgr.GetWebhookServer().Register("/mutate-aimservice", &admission.Webhook{
		Handler: &aimservice.Webhook{Client: client, Decoder: decoder, Logger: logger.WithName("aimservice-webhook")},
	})
	return nil
}
