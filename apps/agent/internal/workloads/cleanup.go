// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package workloads

import (
	"context"
	"errors"

	"github.com/go-logr/logr"
	agent "github.com/silogen/agent/internal/common"
	common "github.com/silogen/agent/internal/workloads/common"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	"k8s.io/client-go/discovery/cached/memory"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/restmapper"
)

// Cleanup strips the workload finalizer from all workload resources in AIRM-managed namespaces.
func Cleanup(ctx context.Context, clientset kubernetes.Interface, dynamicClient dynamic.Interface, log logr.Logger, dryRun bool) error {
	mapper := restmapper.NewDeferredDiscoveryRESTMapper(
		memory.NewMemCacheClient(clientset.Discovery()),
	)

	namespaces, err := agent.ListManagedNamespaceNames(ctx, clientset)
	if err != nil {
		return err
	}

	var errs []error
	for _, gk := range KnownComponentGroupKinds {
		mapping, err := mapper.RESTMapping(gk, "")
		if err != nil {
			log.Info("resource not installed, skipping", "groupKind", gk.String())
			continue
		}
		if mapping.Scope.Name() != apimeta.RESTScopeNameNamespace {
			continue
		}
		for _, ns := range namespaces {
			if err := agent.StripFinalizer(ctx, dynamicClient, log, dryRun, mapping.Resource, ns, common.WorkloadFinalizer); err != nil {
				errs = append(errs, err)
			}
		}
	}
	return errors.Join(errs...)
}
