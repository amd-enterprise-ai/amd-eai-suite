// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package config

import (
	"fmt"
	"os"
	"strconv"

	"github.com/go-logr/logr"
	"github.com/joho/godotenv"
)

type AgentConfig struct {
	ClusterQueue        RabbitMQConfig
	CommonFeedbackQueue RabbitMQConfig
	ClusterName         string
	HTTPPort            int
	HealthCheckPort     int
}

type WebhookConfig struct {
	WebhookPort     int
	WebhookCertPath string
	HealthCheckPort int
}

type RabbitMQConfig struct {
	Host     string
	Port     int
	User     string
	Password string
	VHost    string
	Queue    string
}

// LoadAgentConfig loads configuration
func LoadAgentConfig(logger logr.Logger) (*AgentConfig, error) {
	// Try to load .env file (ignore error if file doesn't exist)
	if err := godotenv.Load(); err != nil {
		logger.V(1).Info("no .env file found, using environment variables only")
	}

	user := os.Getenv("RABBITMQ_USER")
	if user == "" {
		return nil, fmt.Errorf("RABBITMQ_USER required")
	}

	host := getEnv("RABBITMQ_HOST", "localhost")

	password := os.Getenv("RABBITMQ_PASSWORD")
	if password == "" {
		return nil, fmt.Errorf("RABBITMQ_PASSWORD required")
	}

	port := getEnvAsInt("RABBITMQ_PORT", 5672)

	clusterName := os.Getenv("KUBE_CLUSTER_NAME")
	if clusterName == "" {
		return nil, fmt.Errorf("KUBE_CLUSTER_NAME required")
	}

	httpPort := getEnvAsInt("HTTP_PORT", 8000)
	healthPort := getEnvAsInt("HEALTH_PORT", 8081)

	return &AgentConfig{
		ClusterQueue: RabbitMQConfig{
			Host:     host,
			Port:     port,
			User:     user,
			Password: password,
			VHost:    fmt.Sprintf("vh_%s", user),
			Queue:    user,
		},
		CommonFeedbackQueue: RabbitMQConfig{
			Host:     host,
			Port:     port,
			User:     user,
			Password: password,
			VHost:    getEnv("RABBITMQ_AIRM_COMMON_VHOST", "vh_airm_common"),
			Queue:    getEnv("RABBITMQ_AIRM_COMMON_QUEUE", "airm_common"),
		},
		ClusterName:     clusterName,
		HTTPPort:        httpPort,
		HealthCheckPort: healthPort,
	}, nil
}

// LoadWebhookConfig loads webhook configuration.
func LoadWebhookConfig(logger logr.Logger) (*WebhookConfig, error) {
	// Try to load .env file (ignore error if file doesn't exist)
	if err := godotenv.Load(); err != nil {
		logger.V(1).Info("no .env file found, using environment variables only")
	}

	webhookPort := getEnvAsInt("WEBHOOK_PORT", 9443)
	webhooksCertPath := getEnv("WEBHOOKS_CERT_PATH", "/etc/mutating-webhook/tls/")
	healthPort := getEnvAsInt("HEALTH_PORT", 8081)

	return &WebhookConfig{
		WebhookPort:     webhookPort,
		WebhookCertPath: webhooksCertPath,
		HealthCheckPort: healthPort,
	}, nil
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func getEnvAsInt(name string, defaultVal int) int {
	if val, err := strconv.Atoi(os.Getenv(name)); err == nil {
		return val
	}
	return defaultVal
}
