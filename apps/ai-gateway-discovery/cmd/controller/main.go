// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package main

import (
	"fmt"
	"os"

	"github.com/silogen/ai-gateway-discovery/internal/config"
	"github.com/silogen/ai-gateway-discovery/internal/controller"
	"k8s.io/apimachinery/pkg/runtime"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	clientgoscheme "k8s.io/client-go/kubernetes/scheme"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/healthz"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"
	metricsserver "sigs.k8s.io/controller-runtime/pkg/metrics/server"
)

var scheme = runtime.NewScheme()

func init() {
	// Only standard Kubernetes types are needed; InferenceService and Envoy AI
	// Gateway resources are accessed entirely via unstructured.Unstructured.
	utilruntime.Must(clientgoscheme.AddToScheme(scheme))
}

func main() {
	logger := zap.New(zap.UseDevMode(false))
	ctrl.SetLogger(logger)

	cfg, err := config.Load()
	if err != nil {
		logger.Error(err, "failed to load config")
		os.Exit(1)
	}

	mgr, err := ctrl.NewManager(ctrl.GetConfigOrDie(), ctrl.Options{
		Scheme:                 scheme,
		LeaderElection:         false,
		HealthProbeBindAddress: fmt.Sprintf(":%d", cfg.HealthPort),
		Metrics: metricsserver.Options{
			BindAddress: "0",
		},
	})
	if err != nil {
		logger.Error(err, "failed to create manager")
		os.Exit(1)
	}

	if err := (&controller.InferenceServiceReconciler{
		Client: mgr.GetClient(),
		Config: cfg,
		Log:    logger.WithName("InferenceServiceReconciler"),
	}).SetupWithManager(mgr); err != nil {
		logger.Error(err, "failed to setup InferenceServiceReconciler")
		os.Exit(1)
	}

	if err := mgr.AddHealthzCheck("healthz", healthz.Ping); err != nil {
		logger.Error(err, "failed to set up health check")
		os.Exit(1)
	}
	if err := mgr.AddReadyzCheck("readyz", healthz.Ping); err != nil {
		logger.Error(err, "failed to set up ready check")
		os.Exit(1)
	}

	logger.Info("starting AiGatewayDiscovery",
		"targetNamespace", cfg.TargetNamespace,
		"managedLabel", cfg.ManagedLabelName+"="+cfg.ManagedLabelValue,
	)

	if err := mgr.Start(ctrl.SetupSignalHandler()); err != nil {
		logger.Error(err, "manager exited with error")
		os.Exit(1)
	}
}
