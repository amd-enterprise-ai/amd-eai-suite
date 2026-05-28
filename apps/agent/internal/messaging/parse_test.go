// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package messaging

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestParseMessageEnvelope_SecretMessages(t *testing.T) {
	tests := []struct {
		name        string
		messageType MessageType
		payload     string
	}{
		{
			name:        "project_secrets_create",
			messageType: MessageTypeProjectSecretsCreate,
			payload:     `{"message_type":"project_secrets_create","project_name":"test","secret_name":"test-secret"}`,
		},
		{
			name:        "project_secrets_delete",
			messageType: MessageTypeProjectSecretsDelete,
			payload:     `{"message_type":"project_secrets_delete","project_secret_id":"123"}`,
		},
		{
			name:        "project_secrets_update",
			messageType: MessageTypeProjectSecretsUpdate,
			payload:     `{"message_type":"project_secrets_update","project_secret_id":"123","status":"Synced"}`,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rawMsg, err := ParseMessageEnvelope([]byte(tt.payload))
			require.NoError(t, err)
			assert.Equal(t, tt.messageType, rawMsg.Type)
			assert.Equal(t, tt.payload, string(rawMsg.Payload))
		})
	}
}
