// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package k8ssecret

import (
	"k8s.io/apimachinery/pkg/runtime/schema"

	common "github.com/silogen/agent/internal/secrets/common"
)

var GroupKind = schema.GroupKind{Group: "", Kind: "Secret"}

const Finalizer = common.SecretFinalizer
