// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package common

import (
	"context"
	"fmt"

	corev1 "k8s.io/api/core/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	"sigs.k8s.io/controller-runtime/pkg/predicate"
)

// ManagedNamespaceEventFilter returns a predicate that filters events based on namespace labels.
func ManagedNamespaceEventFilter(c client.Client) predicate.Predicate {
	return predicate.NewPredicateFuncs(func(obj client.Object) bool {
		ns := &corev1.Namespace{}
		if err := c.Get(context.Background(), client.ObjectKey{Name: obj.GetNamespace()}, ns); err != nil {
			return false
		}

		nsLabels := ns.GetLabels()
		if nsLabels == nil {
			return false
		}
		_, hasLabel := nsLabels[ProjectIDLabel]
		return hasLabel
	})
}

// RemoveFinalizer removes the provided finalizer from the object using a patch.
func RemoveFinalizer(
	ctx context.Context,
	c client.Client,
	obj client.Object,
	finalizer string,
) error {
	if !controllerutil.ContainsFinalizer(obj, finalizer) {
		return nil
	}

	baseObj := obj.DeepCopyObject()
	base, ok := baseObj.(client.Object)
	if !ok {
		return fmt.Errorf("failed to deep copy object: expected client.Object, got %T", baseObj)
	}

	controllerutil.RemoveFinalizer(obj, finalizer)
	return c.Patch(ctx, obj, client.MergeFrom(base))
}

// AddFinalizerIfNeeded adds the provided finalizer to the object if the object does not have the finalizer.
func AddFinalizerIfNeeded(
	ctx context.Context,
	c client.Client,
	obj client.Object,
	finalizer string,
) error {
	if !controllerutil.ContainsFinalizer(obj, finalizer) {
		// deep copy the object to avoid modifying the original object
		// use a patch (instead of Update) so we only modify the finalizers field
		baseObj := obj.DeepCopyObject()
		base, ok := baseObj.(client.Object)
		if !ok {
			return fmt.Errorf("failed to deep copy object: expected client.Object, got %T", baseObj)
		}
		controllerutil.AddFinalizer(obj, finalizer)
		return c.Patch(ctx, obj, client.MergeFrom(base))
	}
	return nil
}
