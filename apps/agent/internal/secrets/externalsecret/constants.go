// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package externalsecret

import (
	"k8s.io/apimachinery/pkg/runtime/schema"

	common "github.com/silogen/agent/internal/secrets/common"
)

var GroupKind = schema.GroupKind{Group: "external-secrets.io", Kind: "ExternalSecret"}

const (
	Finalizer = common.SecretFinalizer
	crdName   = "externalsecrets.external-secrets.io"
)
