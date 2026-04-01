// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package http

import (
	"context"
	"fmt"
	"net/http"
	"time"

	"github.com/go-logr/logr"
	"github.com/silogen/agent/internal/config"
	"github.com/silogen/agent/internal/heartbeat"
	"github.com/silogen/agent/internal/kubernetes"
	"github.com/silogen/agent/internal/messaging"
)

// Server wraps an HTTP server for the cluster agent.
type Server struct {
	server *http.Server
	logger logr.Logger
}

// NewServer creates a new HTTP server.
func NewServer(
	cfg *config.AgentConfig,
	publisher *messaging.Publisher,
	k8sClient *kubernetes.Client,
	logger logr.Logger,
) *Server {
	// Create heartbeat publisher for HTTP handlers
	logger.Info("initializing component", "component", "heartbeat-publisher")
	heartbeatPub := heartbeat.NewPublisher(publisher, k8sClient, cfg.ClusterName, logger)

	// Create HTTP handler for heartbeats
	logger.Info("initializing component", "component", "http-handler")
	httpRouter := heartbeat.NewHTTPRouter(heartbeatPub, logger)

	mux := http.NewServeMux()
	mux.HandleFunc("/heartbeats", httpRouter.HandleHeartbeat)

	server := &http.Server{
		Addr:         fmt.Sprintf(":%d", cfg.HTTPPort),
		Handler:      mux,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	return &Server{
		server: server,
		logger: logger,
	}
}

func (s *Server) Start(ctx context.Context) error {
	// Run shutdown in separate goroutine
	go func() {
		<-ctx.Done()
		s.logger.Info("shutting down HTTP server")

		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		if err := s.server.Shutdown(shutdownCtx); err != nil {
			s.logger.Error(err, "HTTP server shutdown error")
		}
	}()

	// Block here running the server (on the errgroup goroutine)
	s.logger.Info("starting HTTP server", "addr", s.server.Addr)
	if err := s.server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		return err
	}

	return nil
}
