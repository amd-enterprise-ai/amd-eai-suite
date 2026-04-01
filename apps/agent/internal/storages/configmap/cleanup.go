// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package configmap

import (
	"context"
	"errors"

	"github.com/go-logr/logr"
	agent "github.com/silogen/agent/internal/common"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
)

// Cleanup strips the storage configmap finalizer from AIRM storage configmaps in managed namespaces.
func Cleanup(ctx context.Context, clientset kubernetes.Interface, dynamicClient dynamic.Interface, log logr.Logger, dryRun bool) error {
	namespaces, err := agent.ListManagedNamespaceNames(ctx, clientset)
	if err != nil {
		return err
	}
	var errs []error
	for _, ns := range namespaces {
		if err := agent.StripFinalizer(ctx, dynamicClient, log, dryRun, configMapGVR, ns, ConfigMapFinalizer); err != nil {
			errs = append(errs, err)
		}
	}
	return errors.Join(errs...)
}
