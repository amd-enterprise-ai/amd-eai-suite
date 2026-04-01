// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package secrets

import (
	"github.com/go-logr/logr"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/webhook/admission"

	"github.com/silogen/agent/internal/secrets/externalsecret"
	"github.com/silogen/agent/internal/secrets/k8ssecret"
)

func SetupWebhooks(mgr ctrl.Manager, logger logr.Logger) error {
	decoder := admission.NewDecoder(mgr.GetScheme())
	client := mgr.GetClient()

	mgr.GetWebhookServer().Register("/mutate-secret", &admission.Webhook{
		Handler: &k8ssecret.Webhook{Client: client, Decoder: decoder, Logger: logger.WithName("secret-webhook")},
	})
	mgr.GetWebhookServer().Register("/mutate-externalsecret", &admission.Webhook{
		Handler: &externalsecret.Webhook{Client: client, Decoder: decoder, Logger: logger.WithName("externalsecret-webhook")},
	})
	return nil
}
