// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package heartbeat

import (
	"encoding/json"
	"testing"
	"time"

	"github.com/silogen/agent/internal/messaging"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestHeartbeatMessage_MarshalJSON(t *testing.T) {
	now := time.Now().UTC()
	msg := &HeartbeatMessage{
		MessageType:     messaging.MessageTypeHeartbeat,
		LastHeartbeatAt: now,
		ClusterName:     "test-cluster",
	}

	data, err := json.Marshal(msg)
	require.NoError(t, err)

	var unmarshaled HeartbeatMessage
	err = json.Unmarshal(data, &unmarshaled)
	require.NoError(t, err)

	assert.Equal(t, msg.MessageType, unmarshaled.MessageType)
	assert.Equal(t, msg.ClusterName, unmarshaled.ClusterName)
	assert.WithinDuration(t, msg.LastHeartbeatAt, unmarshaled.LastHeartbeatAt, time.Second)
}
