// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package config

import (
	"os"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"
)

func TestLoadAgentConfig(t *testing.T) {
	logger := zap.New(zap.UseDevMode(true))
	tests := []struct {
		name        string
		envVars     map[string]string
		wantErr     bool
		errContains string
		validate    func(*testing.T, *AgentConfig)
	}{
		{
			name: "valid config with defaults",
			envVars: map[string]string{
				"RABBITMQ_USER":     "testuser",
				"RABBITMQ_PASSWORD": "testpass",
				"KUBE_CLUSTER_NAME": "test-cluster",
			},
			validate: func(t *testing.T, cfg *AgentConfig) {
				assert.Equal(t, "testuser", cfg.ClusterQueue.User)
				assert.Equal(t, "testpass", cfg.ClusterQueue.Password)
				assert.Equal(t, "localhost", cfg.ClusterQueue.Host)
				assert.Equal(t, 5672, cfg.ClusterQueue.Port)
				assert.Equal(t, "vh_testuser", cfg.ClusterQueue.VHost)
				assert.Equal(t, "testuser", cfg.ClusterQueue.Queue)
				assert.Equal(t, "vh_airm_common", cfg.CommonFeedbackQueue.VHost)
				assert.Equal(t, "airm_common", cfg.CommonFeedbackQueue.Queue)
				assert.Equal(t, "test-cluster", cfg.ClusterName)
				assert.Equal(t, 8000, cfg.HTTPPort)
				assert.Equal(t, 8081, cfg.HealthCheckPort)
			},
		},
		{
			name: "valid config with custom values",
			envVars: map[string]string{
				"RABBITMQ_USER":              "customuser",
				"RABBITMQ_PASSWORD":          "custompass",
				"RABBITMQ_HOST":              "rabbitmq.example.com",
				"RABBITMQ_PORT":              "5673",
				"RABBITMQ_AIRM_COMMON_VHOST": "vh_custom",
				"RABBITMQ_AIRM_COMMON_QUEUE": "custom_queue",
				"KUBE_CLUSTER_NAME":          "custom-cluster",
				"HEALTH_PORT":                "8001",
			},
			validate: func(t *testing.T, cfg *AgentConfig) {
				assert.Equal(t, "customuser", cfg.ClusterQueue.User)
				assert.Equal(t, "custompass", cfg.ClusterQueue.Password)
				assert.Equal(t, "rabbitmq.example.com", cfg.ClusterQueue.Host)
				assert.Equal(t, 5673, cfg.ClusterQueue.Port)
				assert.Equal(t, "rabbitmq.example.com", cfg.CommonFeedbackQueue.Host)
				assert.Equal(t, 5673, cfg.CommonFeedbackQueue.Port)
				assert.Equal(t, "customuser", cfg.CommonFeedbackQueue.User)
				assert.Equal(t, "custompass", cfg.CommonFeedbackQueue.Password)
				assert.Equal(t, "vh_custom", cfg.CommonFeedbackQueue.VHost)
				assert.Equal(t, "custom_queue", cfg.CommonFeedbackQueue.Queue)
				assert.Equal(t, "custom-cluster", cfg.ClusterName)
				assert.Equal(t, 8000, cfg.HTTPPort)
				assert.Equal(t, 8001, cfg.HealthCheckPort)
			},
		},
		{
			name: "missing RABBITMQ_USER",
			envVars: map[string]string{
				"RABBITMQ_PASSWORD": "testpass",
			},
			wantErr:     true,
			errContains: "RABBITMQ_USER required",
		},
		{
			name: "missing RABBITMQ_PASSWORD",
			envVars: map[string]string{
				"RABBITMQ_USER": "testuser",
			},
			wantErr:     true,
			errContains: "RABBITMQ_PASSWORD required",
		},
		{
			name: "missing KUBE_CLUSTER_NAME",
			envVars: map[string]string{
				"RABBITMQ_USER":     "testuser",
				"RABBITMQ_PASSWORD": "testpass",
			},
			wantErr:     true,
			errContains: "KUBE_CLUSTER_NAME required",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Save original env vars
			originalEnv := make(map[string]string)
			for k := range tt.envVars {
				if v := os.Getenv(k); v != "" {
					originalEnv[k] = v
				}
			}

			// Clear relevant env vars
			for k := range tt.envVars {
				os.Unsetenv(k)
			}

			// Set test env vars
			for k, v := range tt.envVars {
				os.Setenv(k, v)
			}

			// Cleanup
			defer func() {
				for k := range tt.envVars {
					os.Unsetenv(k)
				}
				for k, v := range originalEnv {
					os.Setenv(k, v)
				}
			}()

			cfg, err := LoadAgentConfig(logger)

			if tt.wantErr {
				require.Error(t, err)
				if tt.errContains != "" {
					assert.Contains(t, err.Error(), tt.errContains)
				}
				return
			}

			require.NoError(t, err)
			require.NotNil(t, cfg)
			if tt.validate != nil {
				tt.validate(t, cfg)
			}
		})
	}
}

func TestLoadWebhookConfig(t *testing.T) {
	logger := zap.New(zap.UseDevMode(true))

	tests := []struct {
		name     string
		envVars  map[string]string
		validate func(*testing.T, *WebhookConfig)
	}{
		{
			name:    "valid config with defaults",
			envVars: map[string]string{},
			validate: func(t *testing.T, cfg *WebhookConfig) {
				assert.Equal(t, 9443, cfg.WebhookPort)
				assert.Equal(t, "/etc/mutating-webhook/tls/", cfg.WebhookCertPath)
				assert.Equal(t, 8081, cfg.HealthCheckPort)
			},
		},
		{
			name: "valid config with custom values",
			envVars: map[string]string{
				"WEBHOOK_PORT":       "9442",
				"WEBHOOKS_CERT_PATH": "/custom/path",
				"HEALTH_PORT":        "8001",
			},
			validate: func(t *testing.T, cfg *WebhookConfig) {
				assert.Equal(t, 9442, cfg.WebhookPort)
				assert.Equal(t, "/custom/path", cfg.WebhookCertPath)
				assert.Equal(t, 8001, cfg.HealthCheckPort)
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Save original env vars
			originalEnv := make(map[string]string)
			for k := range tt.envVars {
				if v := os.Getenv(k); v != "" {
					originalEnv[k] = v
				}
			}

			// Clear relevant env vars
			for k := range tt.envVars {
				os.Unsetenv(k)
			}

			// Set test env vars
			for k, v := range tt.envVars {
				os.Setenv(k, v)
			}

			// Cleanup
			defer func() {
				for k := range tt.envVars {
					os.Unsetenv(k)
				}
				for k, v := range originalEnv {
					os.Setenv(k, v)
				}
			}()

			cfg, err := LoadWebhookConfig(logger)

			require.NoError(t, err)
			require.NotNil(t, cfg)
			if tt.validate != nil {
				tt.validate(t, cfg)
			}
		})
	}
}

func TestGetEnv(t *testing.T) {
	tests := []struct {
		name     string
		key      string
		fallback string
		setValue string
		want     string
	}{
		{
			name:     "env var set",
			key:      "TEST_VAR",
			fallback: "fallback",
			setValue: "actual",
			want:     "actual",
		},
		{
			name:     "env var not set",
			key:      "TEST_VAR_NOT_SET",
			fallback: "fallback",
			setValue: "",
			want:     "fallback",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if tt.setValue != "" {
				os.Setenv(tt.key, tt.setValue)
				defer os.Unsetenv(tt.key)
			} else {
				os.Unsetenv(tt.key)
			}

			got := getEnv(tt.key, tt.fallback)
			assert.Equal(t, tt.want, got)
		})
	}
}
