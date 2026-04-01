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
	"github.com/silogen/agent/internal/secrets"
	"github.com/silogen/agent/internal/workloads"
	"golang.org/x/sync/errgroup"
	"k8s.io/apimachinery/pkg/runtime"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	clientgoscheme "k8s.io/client-go/kubernetes/scheme"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/healthz"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"
	metricsserver "sigs.k8s.io/controller-runtime/pkg/metrics/server"
	gatewayv1 "sigs.k8s.io/gateway-api/apis/v1"

	"github.com/silogen/agent/internal/config"
	"github.com/silogen/agent/internal/handlers"
	"github.com/silogen/agent/internal/heartbeat"
	"github.com/silogen/agent/internal/http"
	"github.com/silogen/agent/internal/kubernetes"
	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/namespaces"
	"github.com/silogen/agent/internal/nodes"
	"github.com/silogen/agent/internal/quotas"
	storages "github.com/silogen/agent/internal/storages/configmap"
	kaiwov1alpha1 "github.com/silogen/kaiwo/apis/kaiwo/v1alpha1"
)

var (
	scheme = runtime.NewScheme()
)

func init() {
	utilruntime.Must(clientgoscheme.AddToScheme(scheme))
	utilruntime.Must(kaiwov1alpha1.AddToScheme(scheme))
	utilruntime.Must(aimv1alpha1.AddToScheme(scheme))
	utilruntime.Must(gatewayv1.Install(scheme))
}

func publishStartupMessages(
	ctx context.Context,
	logger logr.Logger,
	publisher *messaging.Publisher,
	k8sClient *kubernetes.Client,
	cfg *config.AgentConfig,
) error {
	logger.Info("sending initial heartbeat on startup")
	heartbeatPub := heartbeat.NewPublisher(publisher, k8sClient, cfg.ClusterName, logger)
	if err := heartbeatPub.Publish(ctx); err != nil {
		logger.Error(err, "failed to send initial heartbeat")
		return err
	}

	logger.Info("sending initial cluster node information on startup")
	if err := nodes.PublishClusterNodes(ctx, publisher, k8sClient, logger); err != nil {
		logger.Error(err, "failed to send initial cluster nodes")
		return err
	}
	return nil
}

func setupControllers(ctx context.Context, k8sClient *kubernetes.Client, mgr ctrl.Manager, publisher *messaging.Publisher, logger logr.Logger) error {
	// Setup namespace controller
	logger.Info("initializing component", "component", "namespace-controller")
	if err := (&namespaces.NamespaceReconciler{
		Client:    mgr.GetClient(),
		Publisher: publisher,
	}).SetupWithManager(mgr); err != nil {
		return err
	}

	logger.Info("initializing component", "component", "kaiwoqueueconfig-controller")
	if err := (&quotas.KaiwoQueueConfigReconciler{
		Client:    mgr.GetClient(),
		Publisher: publisher,
	}).SetupWithManager(mgr); err != nil {
		return err
	}

	// Setup node controller
	logger.Info("initializing component", "component", "node-controller")
	if err := (&nodes.NodeReconciler{
		Client:    mgr.GetClient(),
		Publisher: publisher,
	}).SetupWithManager(mgr); err != nil {
		return err
	}

	// Setup storages-configmap controller
	logger.Info("initializing component", "component", "storages-configmap-controller")
	if err := (&storages.ConfigMapReconciler{
		Client:    mgr.GetClient(),
		Publisher: publisher,
	}).SetupWithManager(mgr); err != nil {
		return err
	}

	// Setup workload controllers
	if err := workloads.SetupControllers(mgr, publisher, logger); err != nil {
		return err
	}

	// Setup secret controllers
	if err := secrets.SetupControllers(ctx, mgr, publisher, k8sClient, logger); err != nil {
		return err
	}

	return nil
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

func setupHTTPServer(
	logger logr.Logger,
	cfg *config.AgentConfig,
	publisher *messaging.Publisher,
	k8sClient *kubernetes.Client,
) *http.Server {
	logger.Info("initializing component", "component", "http-server")
	httpServer := http.NewServer(cfg, publisher, k8sClient, logger)
	return httpServer
}

func main() {
	logger := zap.New(zap.UseDevMode(false))

	cfg, err := config.LoadAgentConfig(logger)
	if err != nil {
		logger.Error(err, "config error")
		os.Exit(1)
	}

	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()

	logger.Info("starting agent")

	ctrl.SetLogger(logger)

	// Initialize Kubernetes client (for legacy components)
	logger.Info("initializing component", "component", "kubernetes-client")
	k8sClient, err := kubernetes.NewClient(logger)
	if err != nil {
		logger.Error(err, "kubernetes client init failed")
		os.Exit(1)
	}

	// Create publisher for common feedback queue
	logger.Info("initializing component", "component", "publisher")
	publisher := messaging.NewPublisher(
		cfg.CommonFeedbackQueue,
		logger,
	)
	defer publisher.Close()

	// Connect publisher
	if connectErr := publisher.Connect(ctx); connectErr != nil {
		logger.Error(connectErr, "publisher connect failed")
		os.Exit(1)
	}

	err = publishStartupMessages(ctx, logger, publisher, k8sClient, cfg)
	if err != nil {
		logger.Error(err, "startup messages failed")
		os.Exit(1)
	}

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
	}

	mgr, err := ctrl.NewManager(ctrl.GetConfigOrDie(), mgrOptions)
	if err != nil {
		logger.Error(err, "failed to create controller manager")
		os.Exit(1)
	}

	if err := setupControllers(ctx, k8sClient, mgr, publisher, logger); err != nil {
		logger.Error(err, "failed to setup controllers")
		os.Exit(1)
	}

	if err := setupHealthChecks(mgr, logger); err != nil {
		logger.Error(err, "failed to setup health checks")
		os.Exit(1)
	}

	httpServer := setupHTTPServer(logger, cfg, publisher, k8sClient)

	// Create router with all handlers
	router := handlers.NewRouter(k8sClient.Clientset, k8sClient.DynamicClient, publisher, logger)

	// Create consumer with router as the handler
	consumer := messaging.NewConsumer(
		cfg.ClusterQueue,
		router.Handle,
		logger,
	)
	defer consumer.Close()

	// Start components using errgroup for fail-fast behavior
	g, gCtx := errgroup.WithContext(ctx)

	// Start controller manager
	g.Go(func() error {
		logger.Info("starting controller manager")
		if err := mgr.Start(gCtx); err != nil {
			logger.Error(err, "controller manager error")
			return err
		}
		return nil
	})

	// Start HTTP server
	g.Go(func() error {
		if err := httpServer.Start(gCtx); err != nil && err != context.Canceled {
			logger.Error(err, "HTTP server error")
			return err
		}
		return nil
	})

	// Start consumer
	g.Go(func() error {
		if err := consumer.Start(gCtx); err != nil && err != context.Canceled {
			logger.Error(err, "consumer error")
			return err
		}
		return nil
	})

	// Wait for all goroutines to finish (or first error)
	if err := g.Wait(); err != nil {
		logger.Error(err, "component failed")
	}

	logger.Info("shutdown complete")
}
