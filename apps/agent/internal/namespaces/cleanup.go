// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package namespaces

import (
	"context"

	"github.com/go-logr/logr"
	agent "github.com/silogen/agent/internal/common"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
)

// Cleanup strips the namespace finalizer from all namespaces.
func Cleanup(ctx context.Context, clientset kubernetes.Interface, dynamicClient dynamic.Interface, log logr.Logger, dryRun bool) error {
	return agent.StripFinalizer(ctx, dynamicClient, log, dryRun, namespaceGVR, "", namespaceFinalizer)
}
