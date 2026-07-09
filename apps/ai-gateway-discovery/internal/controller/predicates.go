// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package controller

import (
	"sigs.k8s.io/controller-runtime/pkg/event"
	"sigs.k8s.io/controller-runtime/pkg/predicate"
)

// hasManagedLabel filters events to only InferenceService objects that carry
// the configured managed label. Objects without the label are ignored by the
// InferenceServiceReconciler so unrelated InferenceServices are never touched.
//
// Delete events always pass through regardless of label presence: an IS that
// had its managed label removed while the finalizer is still set must still be
// reconciled so the finalizer cleanup runs and the IS is not stuck terminating.
func hasManagedLabel(labelName, labelValue string) predicate.Predicate {
	hasLabel := func(labels map[string]string) bool {
		return labels[labelName] == labelValue
	}

	return predicate.Funcs{
		CreateFunc: func(e event.CreateEvent) bool {
			return hasLabel(e.Object.GetLabels())
		},
		UpdateFunc: func(e event.UpdateEvent) bool {
			return hasLabel(e.ObjectNew.GetLabels()) || hasLabel(e.ObjectOld.GetLabels())
		},
		DeleteFunc: func(e event.DeleteEvent) bool {
			return true
		},
		GenericFunc: func(e event.GenericEvent) bool {
			return hasLabel(e.Object.GetLabels())
		},
	}
}
