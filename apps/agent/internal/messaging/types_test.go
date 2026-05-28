// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package messaging

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestMessageType_Constants(t *testing.T) {
	assert.Equal(t, MessageType("project_namespace_create"), MessageTypeProjectNamespaceCreate)
	assert.Equal(t, MessageType("project_namespace_delete"), MessageTypeProjectNamespaceDelete)
	assert.Equal(t, MessageType("project_namespace_update"), MessageTypeProjectNamespaceUpdate)
	assert.Equal(t, MessageType("project_namespace_status"), MessageTypeProjectNamespaceStatus)
	assert.Equal(t, MessageType("unmanaged_namespace"), MessageTypeUnmanagedNamespace)
	assert.Equal(t, MessageType("heartbeat"), MessageTypeHeartbeat)
	assert.Equal(t, MessageType("project_secrets_create"), MessageTypeProjectSecretsCreate)
	assert.Equal(t, MessageType("project_secrets_delete"), MessageTypeProjectSecretsDelete)
	assert.Equal(t, MessageType("project_secrets_update"), MessageTypeProjectSecretsUpdate)
}
