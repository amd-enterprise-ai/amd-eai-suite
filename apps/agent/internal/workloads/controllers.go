// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package workloads

import (
	"github.com/go-logr/logr"
	ctrl "sigs.k8s.io/controller-runtime"

	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/workloads/aimservice"
	"github.com/silogen/agent/internal/workloads/configmap"
	"github.com/silogen/agent/internal/workloads/cronjob"
	"github.com/silogen/agent/internal/workloads/daemonset"
	"github.com/silogen/agent/internal/workloads/deployment"
	"github.com/silogen/agent/internal/workloads/httproute"
	"github.com/silogen/agent/internal/workloads/ingress"
	"github.com/silogen/agent/internal/workloads/job"
	"github.com/silogen/agent/internal/workloads/kaiwojob"
	"github.com/silogen/agent/internal/workloads/kaiwoservice"
	"github.com/silogen/agent/internal/workloads/pod"
	"github.com/silogen/agent/internal/workloads/replicaset"
	"github.com/silogen/agent/internal/workloads/service"
	"github.com/silogen/agent/internal/workloads/statefulset"
)

// SetupControllers sets up all workload controllers with the manager.
func SetupControllers(mgr ctrl.Manager, publisher *messaging.Publisher, logger logr.Logger) error {
	logger.Info("initializing component", "component", "pod-controller")
	if err := (&pod.Reconciler{
		Client:    mgr.GetClient(),
		Publisher: publisher,
	}).SetupWithManager(mgr); err != nil {
		return err
	}

	logger.Info("initializing component", "component", "deployment-controller")
	if err := (&deployment.Reconciler{
		Client:    mgr.GetClient(),
		Publisher: publisher,
	}).SetupWithManager(mgr); err != nil {
		return err
	}

	logger.Info("initializing component", "component", "job-controller")
	if err := (&job.Reconciler{
		Client:    mgr.GetClient(),
		Publisher: publisher,
	}).SetupWithManager(mgr); err != nil {
		return err
	}

	logger.Info("initializing component", "component", "statefulset-controller")
	if err := (&statefulset.Reconciler{
		Client:    mgr.GetClient(),
		Publisher: publisher,
	}).SetupWithManager(mgr); err != nil {
		return err
	}

	logger.Info("initializing component", "component", "daemonset-controller")
	if err := (&daemonset.Reconciler{
		Client:    mgr.GetClient(),
		Publisher: publisher,
	}).SetupWithManager(mgr); err != nil {
		return err
	}

	logger.Info("initializing component", "component", "replicaset-controller")
	if err := (&replicaset.Reconciler{
		Client:    mgr.GetClient(),
		Publisher: publisher,
	}).SetupWithManager(mgr); err != nil {
		return err
	}

	logger.Info("initializing component", "component", "cronjob-controller")
	if err := (&cronjob.Reconciler{
		Client:    mgr.GetClient(),
		Publisher: publisher,
	}).SetupWithManager(mgr); err != nil {
		return err
	}

	logger.Info("initializing component", "component", "kaiwojob-controller")
	if err := (&kaiwojob.Reconciler{
		Client:    mgr.GetClient(),
		Publisher: publisher,
	}).SetupWithManager(mgr); err != nil {
		return err
	}

	logger.Info("initializing component", "component", "kaiwoservice-controller")
	if err := (&kaiwoservice.Reconciler{
		Client:    mgr.GetClient(),
		Publisher: publisher,
	}).SetupWithManager(mgr); err != nil {
		return err
	}

	logger.Info("initializing component", "component", "workload-configmap-controller")
	if err := (&configmap.Reconciler{
		Client:    mgr.GetClient(),
		Publisher: publisher,
	}).SetupWithManager(mgr); err != nil {
		return err
	}

	logger.Info("initializing component", "component", "workload-service-controller")
	if err := (&service.Reconciler{
		Client:    mgr.GetClient(),
		Publisher: publisher,
	}).SetupWithManager(mgr); err != nil {
		return err
	}

	logger.Info("initializing component", "component", "workload-ingress-controller")
	if err := (&ingress.Reconciler{
		Client:    mgr.GetClient(),
		Publisher: publisher,
	}).SetupWithManager(mgr); err != nil {
		return err
	}

	logger.Info("initializing component", "component", "aimservice-controller")
	if err := (&aimservice.Reconciler{
		Client:    mgr.GetClient(),
		Publisher: publisher,
	}).SetupWithManager(mgr); err != nil {
		return err
	}

	logger.Info("initializing component", "component", "httproute-controller")
	if err := (&httproute.Reconciler{
		Client:    mgr.GetClient(),
		Publisher: publisher,
	}).SetupWithManager(mgr); err != nil {
		return err
	}

	return nil
}
