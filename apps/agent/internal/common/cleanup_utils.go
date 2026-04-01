// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package common

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"

	"github.com/go-logr/logr"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
)

// ListManagedNamespaceNames returns the names of all namespaces labeled with ProjectIDLabel.
func ListManagedNamespaceNames(ctx context.Context, clientset kubernetes.Interface) ([]string, error) {
	nsList, err := clientset.CoreV1().Namespaces().List(ctx, metav1.ListOptions{
		LabelSelector: ProjectIDLabel,
	})
	if err != nil {
		return nil, fmt.Errorf("list managed namespaces: %w", err)
	}
	names := make([]string, len(nsList.Items))
	for i := range nsList.Items {
		names[i] = nsList.Items[i].Name
	}
	return names, nil
}

// StripFinalizer removes finalizer from all resources matching gvr in the given namespace.
// Pass empty namespace for cluster-scoped resources.
func StripFinalizer(
	ctx context.Context, dynamicClient dynamic.Interface, log logr.Logger, dryRun bool,
	gvr schema.GroupVersionResource, namespace, finalizer string,
) error {
	client := resourceClient(dynamicClient, gvr, namespace)

	list, err := client.List(ctx, metav1.ListOptions{})
	if err != nil {
		if apierrors.IsNotFound(err) {
			log.Info("resource type not installed, skipping", "gvr", gvr.String())
			return nil
		}
		return fmt.Errorf("list %s in %s: %w", gvr.Resource, namespace, err)
	}

	var errs []error
	for i := range list.Items {
		item := &list.Items[i]
		if !containsFinalizer(item.GetFinalizers(), finalizer) {
			continue
		}

		if dryRun {
			log.Info("[dry-run] would strip finalizer",
				"gvr", gvr.String(), "namespace", item.GetNamespace(), "name", item.GetName(), "finalizer", finalizer)
			continue
		}

		newFinalizers := removeFinalizer(item.GetFinalizers(), finalizer)
		patch, err := json.Marshal(map[string]interface{}{
			"metadata": map[string]interface{}{
				"finalizers": newFinalizers,
			},
		})
		if err != nil {
			errs = append(errs, fmt.Errorf("marshal patch for %s/%s: %w", item.GetNamespace(), item.GetName(), err))
			continue
		}
		if _, err := client.Patch(ctx, item.GetName(), types.MergePatchType, patch, metav1.PatchOptions{}); err != nil {
			if apierrors.IsNotFound(err) {
				continue
			}
			errs = append(errs, fmt.Errorf("patch %s/%s: %w", item.GetNamespace(), item.GetName(), err))
			continue
		}
		log.Info("stripped finalizer",
			"gvr", gvr.String(), "namespace", item.GetNamespace(), "name", item.GetName(), "finalizer", finalizer)
	}
	return errors.Join(errs...)
}

func resourceClient(dynamicClient dynamic.Interface, gvr schema.GroupVersionResource, namespace string) dynamic.ResourceInterface {
	if namespace == "" {
		return dynamicClient.Resource(gvr)
	}
	return dynamicClient.Resource(gvr).Namespace(namespace)
}

func containsFinalizer(finalizers []string, target string) bool {
	for _, f := range finalizers {
		if f == target {
			return true
		}
	}
	return false
}

func removeFinalizer(finalizers []string, target string) []string {
	var result []string
	for _, f := range finalizers {
		if f != target {
			result = append(result, f)
		}
	}
	return result
}
