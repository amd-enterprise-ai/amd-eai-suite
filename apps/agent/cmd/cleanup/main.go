// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"github.com/go-logr/logr"
	"github.com/silogen/agent/internal/kubernetes"
	"github.com/silogen/agent/internal/namespaces"
	"github.com/silogen/agent/internal/quotas"
	"github.com/silogen/agent/internal/secrets"
	storages "github.com/silogen/agent/internal/storages/configmap"
	"github.com/silogen/agent/internal/workloads"
	"k8s.io/client-go/dynamic"
	k8s "k8s.io/client-go/kubernetes"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"
)

func main() {
	var dryRun bool

	flag.BoolVar(&dryRun, "dry-run", false, "Print actions without executing them")
	flag.Usage = func() {
		fmt.Fprintf(os.Stderr, "Usage: %s [OPTIONS]\n\n", os.Args[0])
		fmt.Fprintln(os.Stderr, "Clean uninstall of agent-created AIRM resources.")
		fmt.Fprintln(os.Stderr, "Strips all AIRM finalizers so resources are not stuck in Terminating.")
		fmt.Fprintln(os.Stderr, "Options:")
		flag.PrintDefaults()
	}
	flag.Parse()

	logger := zap.New(zap.UseDevMode(false))

	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()

	k8sClient, err := kubernetes.NewClient(logger)
	if err != nil {
		logger.Error(err, "failed to initialize kubernetes client")
		os.Exit(1)
	}

	logger.Info("starting AIRM agent cleanup", "dry_run", dryRun)

	failed := false
	for _, fn := range []func(context.Context, k8s.Interface, dynamic.Interface, logr.Logger, bool) error{
		namespaces.Cleanup,
		workloads.Cleanup,
		secrets.Cleanup,
		storages.Cleanup,
		quotas.Cleanup,
	} {
		if err := fn(ctx, k8sClient.Clientset, k8sClient.DynamicClient, logger, dryRun); err != nil {
			logger.Error(err, "cleanup failed")
			failed = true
		}
	}

	if failed {
		logger.Info("AIRM agent cleanup finished with errors")
		os.Exit(1)
	}
	logger.Info("AIRM agent cleanup complete")
}
