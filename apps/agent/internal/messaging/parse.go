// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package messaging

import (
	"encoding/json"
	"fmt"
)

type MessageEnvelope struct {
	MessageType MessageType `json:"message_type"`
}

type RawMessage struct {
	Type    MessageType
	Payload []byte
}

func ParseMessageEnvelope(data []byte) (*RawMessage, error) {
	var envelope MessageEnvelope
	if err := json.Unmarshal(data, &envelope); err != nil {
		return nil, fmt.Errorf("failed to parse message: %w", err)
	}

	if envelope.MessageType == "" {
		return nil, fmt.Errorf("message_type is required")
	}

	return &RawMessage{
		Type:    envelope.MessageType,
		Payload: data,
	}, nil
}
