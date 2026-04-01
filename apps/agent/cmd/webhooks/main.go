// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	aimv1alpha1 "github.com/amd-enterprise-ai/aim-engine/api/v1alpha1"
	"github.com/go-logr/logr"
	"github.com/silogen/agent/internal/config"
	"github.com/silogen/agent/internal/secrets"
	"github.com/silogen/agent/internal/workloads"
	kaiwov1alpha1 "github.com/silogen/kaiwo/apis/kaiwo/v1alpha1"
	"k8s.io/apimachinery/pkg/runtime"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	clientgoscheme "k8s.io/client-go/kubernetes/scheme"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/healthz"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"
	metricsserver "sigs.k8s.io/controller-runtime/pkg/metrics/server"
	"sigs.k8s.io/controller-runtime/pkg/webhook"
)

var (
	scheme = runtime.NewScheme()
)

func init() {
	utilruntime.Must(clientgoscheme.AddToScheme(scheme))
	utilruntime.Must(kaiwov1alpha1.AddToScheme(scheme))
	utilruntime.Must(aimv1alpha1.AddToScheme(scheme))
}

func setupHealthChecks(mgr ctrl.Manager, logger logr.Logger) error {
	if err := mgr.AddHealthzCheck("healthz", healthz.Ping); err != nil {
		logger.Error(err, "unable to set up health check")
		return err
	}
	if err := mgr.AddReadyzCheck("readyz", healthz.Ping); err != nil {
		logger.Error(err, "unable to set up ready check")
		return err
	}
	return nil
}

func main() {
	logger := zap.New(zap.UseDevMode(false))

	cfg, err := config.LoadWebhookConfig(logger)
	if err != nil {
		logger.Error(err, "config error")
		os.Exit(1)
	}

	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()

	logger.Info("starting webhook server")

	ctrl.SetLogger(logger)

	logger.Info("initializing component", "component", "controller-manager")

	mgrOptions := ctrl.Options{
		Scheme: scheme,
		// Disable leader election (single instance per cluster)
		LeaderElection:         false,
		HealthProbeBindAddress: fmt.Sprintf(":%d", cfg.HealthCheckPort),
		// Disable metrics server
		Metrics: metricsserver.Options{
			BindAddress: "0",
		},
		WebhookServer: webhook.NewServer(webhook.Options{
			Port:    cfg.WebhookPort,
			CertDir: cfg.WebhookCertPath,
		}),
	}

	mgr, err := ctrl.NewManager(ctrl.GetConfigOrDie(), mgrOptions)
	if err != nil {
		logger.Error(err, "failed to create controller manager")
		os.Exit(1)
	}

	if err := workloads.SetupWebhooks(mgr, logger); err != nil {
		logger.Error(err, "failed to setup workload webhooks")
		os.Exit(1)
	}

	if err := secrets.SetupWebhooks(mgr, logger); err != nil {
		logger.Error(err, "failed to setup secret webhooks")
		os.Exit(1)
	}

	if err := setupHealthChecks(mgr, logger); err != nil {
		logger.Error(err, "failed to setup health checks")
		os.Exit(1)
	}

	logger.Info("starting manager with webhook server", "port", cfg.WebhookPort)
	if err := mgr.Start(ctx); err != nil {
		logger.Error(err, "failed to run manager")
		os.Exit(1)
	}

	logger.Info("shutdown complete")
}
