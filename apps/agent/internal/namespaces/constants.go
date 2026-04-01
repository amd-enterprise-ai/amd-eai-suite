// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package namespaces

import "k8s.io/apimachinery/pkg/runtime/schema"

var namespaceGVR = schema.GroupVersionResource{Version: "v1", Resource: "namespaces"}

const (
	namespaceFinalizer = "airm.silogen.ai/namespace-finalizer"

	KueueManagedLabel = "kueue-managed"
)
