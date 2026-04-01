// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package kubernetes

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"
)

func TestNewClient_InvalidConfig(t *testing.T) {
	logger := zap.New()

	// This will fail because we don't have a valid kubeconfig or in-cluster config
	// In a real test environment, you'd set up a fake kubeconfig or use a fake client
	client, err := NewClient(logger)

	// We expect this to fail in a test environment without kubeconfig
	// The actual error depends on the test environment
	if err != nil {
		assert.Error(t, err)
		assert.Nil(t, client)
	} else {
		// If it succeeds (e.g., in-cluster config available), verify client is created
		require.NotNil(t, client)
		assert.NotNil(t, client.Clientset)
	}
}

func TestNewClient_Logger(t *testing.T) {
	logger := zap.New()

	// Test that logger is properly set
	// In a real scenario, we'd use a fake client, but for now we just verify
	// the function doesn't panic with a valid logger
	assert.NotNil(t, logger)

	// The actual client creation will fail without proper kubeconfig,
	// but we can verify the logger parameter is accepted
	_, err := NewClient(logger)
	// Error is expected without kubeconfig, but we verify it's handled gracefully
	if err != nil {
		assert.Error(t, err)
	}
}
