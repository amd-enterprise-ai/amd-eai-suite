// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package heartbeat

import (
	"encoding/json"
	"net/http"
	"time"

	"github.com/go-logr/logr"
)

// HTTPRouter handles HTTP requests for heartbeat endpoints.
type HTTPRouter struct {
	heartbeatPublisher *Publisher
	logger             logr.Logger
}

// NewHTTPRouter creates a new HTTP handler.
func NewHTTPRouter(heartbeatPublisher *Publisher, logger logr.Logger) *HTTPRouter {
	return &HTTPRouter{
		heartbeatPublisher: heartbeatPublisher,
		logger:             logger,
	}
}

// HandleHeartbeat handles POST /heartbeats requests to send heartbeat messages.
func (h *HTTPRouter) HandleHeartbeat(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		h.logger.Info("WARN: invalid method for heartbeat endpoint", "method", r.Method)
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	ctx := r.Context()

	if err := h.heartbeatPublisher.Publish(ctx); err != nil {
		h.logger.Error(err, "failed to publish heartbeat")
		http.Error(w, "Failed to send heartbeat", http.StatusInternalServerError)
		return
	}

	// Return the heartbeat message as JSON response
	response := &heartbeatResponse{
		MessageType:     "heartbeat",
		LastHeartbeatAt: time.Now().UTC(),
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusAccepted)
	if err := json.NewEncoder(w).Encode(response); err != nil {
		h.logger.Error(err, "failed to encode response")
	}
}

// heartbeatResponse represents the HTTP response for a heartbeat.
type heartbeatResponse struct {
	MessageType     string    `json:"message_type"`
	LastHeartbeatAt time.Time `json:"last_heartbeat_at"`
}
