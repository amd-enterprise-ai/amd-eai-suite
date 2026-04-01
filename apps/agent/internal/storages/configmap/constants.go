// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package configmap

import "k8s.io/apimachinery/pkg/runtime/schema"

var configMapGVR = schema.GroupVersionResource{Version: "v1", Resource: "configmaps"}

const (
	ProjectStorageIDLabel = "airm.silogen.ai/project-storage-id"
	ConfigMapFinalizer    = "airm.silogen.ai/storages-configmap-finalizer"
)
