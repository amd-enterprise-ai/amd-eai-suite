// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package secrets

import (
	"context"
	"os"

	"github.com/go-logr/logr"
	"github.com/silogen/agent/internal/kubernetes"
	"github.com/silogen/agent/internal/secrets/externalsecret"
	"github.com/silogen/agent/internal/secrets/k8ssecret"
	"k8s.io/apimachinery/pkg/runtime/schema"
	ctrl "sigs.k8s.io/controller-runtime"

	"github.com/silogen/agent/internal/messaging"
)

// SetupControllers sets up all workload controllers with the manager.
func SetupControllers(ctx context.Context, mgr ctrl.Manager, publisher *messaging.Publisher, k8sClient *kubernetes.Client, logger logr.Logger) error {
	logger.Info("initializing component", "component", "kubernetes-secret-controller")
	if err := (&k8ssecret.KubernetesSecretReconciler{
		Client:    mgr.GetClient(),
		Publisher: publisher,
	}).SetupWithManager(mgr); err != nil {
		logger.Error(err, "failed to setup kubernetes secret controller")
		os.Exit(1)
	}

	// Setup externalsecret controller
	logger.Info("initializing component", "component", "external-secret-controller")
	version, installed, err := externalsecret.DiscoverExternalSecretVersion(ctx, k8sClient.DynamicClient)
	if err != nil {
		logger.Error(err, "failed to discover ExternalSecret version from CRD")
		os.Exit(1)
	}
	if !installed {
		logger.Info("skipping external secret controller; ExternalSecret CRD not installed")
	} else {
		if err := (&externalsecret.ExternalSecretReconciler{
			Client:    mgr.GetClient(),
			Publisher: publisher,
			GVK: schema.GroupVersionKind{
				Group:   "external-secrets.io",
				Version: version,
				Kind:    "ExternalSecret",
			},
		}).SetupWithManager(mgr); err != nil {
			logger.Error(err, "failed to setup external secret controller")
			os.Exit(1)
		}
	}

	return nil
}
