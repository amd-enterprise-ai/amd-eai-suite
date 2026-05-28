// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package heartbeat

import (
	"time"

	"github.com/silogen/agent/internal/messaging"
)

type HeartbeatMessage struct {
	MessageType     messaging.MessageType `json:"message_type"`
	LastHeartbeatAt time.Time             `json:"last_heartbeat_at"`
	ClusterName     string                `json:"cluster_name"`
}
