// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package handlers

import (
	"context"

	"github.com/silogen/agent/internal/messaging"
)

// ResourceHandler defines the interface for handling resource messages.
// All resource handlers (namespace, secrets, storage) must implement this.
type ResourceHandler interface {
	HandleCreate(ctx context.Context, msg *messaging.RawMessage) error
	HandleDelete(ctx context.Context, msg *messaging.RawMessage) error
	HandleUpdate(ctx context.Context, msg *messaging.RawMessage) error
}
