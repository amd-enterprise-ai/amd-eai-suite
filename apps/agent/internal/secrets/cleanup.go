// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package secrets

import (
	"context"
	"errors"

	"github.com/go-logr/logr"
	agent "github.com/silogen/agent/internal/common"
	"github.com/silogen/agent/internal/secrets/externalsecret"
	"github.com/silogen/agent/internal/secrets/k8ssecret"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/client-go/discovery/cached/memory"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/restmapper"
)

var knownSecretTypes = []struct {
	groupKind schema.GroupKind
	finalizer string
}{
	{k8ssecret.GroupKind, k8ssecret.Finalizer},
	{externalsecret.GroupKind, externalsecret.Finalizer},
}

// Cleanup strips secret-related finalizers from all AIRM-managed secrets.
func Cleanup(ctx context.Context, clientset kubernetes.Interface, dynamicClient dynamic.Interface, log logr.Logger, dryRun bool) error {
	mapper := restmapper.NewDeferredDiscoveryRESTMapper(
		memory.NewMemCacheClient(clientset.Discovery()),
	)

	namespaces, err := agent.ListManagedNamespaceNames(ctx, clientset)
	if err != nil {
		return err
	}

	var errs []error
	for _, st := range knownSecretTypes {
		mapping, err := mapper.RESTMapping(st.groupKind)
		if err != nil {
			log.Info("resource not installed, skipping", "groupKind", st.groupKind.String())
			continue
		}
		for _, ns := range namespaces {
			if err := agent.StripFinalizer(ctx, dynamicClient, log, dryRun, mapping.Resource, ns, st.finalizer); err != nil {
				errs = append(errs, err)
			}
		}
	}
	return errors.Join(errs...)
}
