// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package kubernetes

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/go-logr/logr"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/util/homedir"
)

type Client struct {
	Clientset     kubernetes.Interface
	DynamicClient dynamic.Interface
	logger        logr.Logger
}

// NewClient creates a new Kubernetes client.
// It tries in-cluster config first, then falls back to kubeconfig file.
func NewClient(logger logr.Logger) (*Client, error) {
	var config *rest.Config
	var err error
	var configType string

	// Try in-cluster config first
	config, err = rest.InClusterConfig()
	if err == nil {
		configType = "in-cluster"
		logger.Info("using in-cluster kubernetes config")
	} else {
		// Fall back to kubeconfig file
		var kubeconfig string
		if kubeconfigPath := os.Getenv("KUBECONFIG"); kubeconfigPath != "" {
			kubeconfig = kubeconfigPath
		} else {
			kubeconfig = filepath.Join(homedir.HomeDir(), ".kube", "config")
		}

		config, err = clientcmd.BuildConfigFromFlags("", kubeconfig)
		if err != nil {
			logger.Error(err, "kubernetes client init failed", "config_type", "kubeconfig")
			return nil, fmt.Errorf("failed to build kubeconfig: %w", err)
		}
		configType = "kubeconfig"
		logger.Info("using kubeconfig file", "path", kubeconfig)
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		logger.Error(err, "kubernetes client init failed", "config_type", configType)
		return nil, fmt.Errorf("failed to create clientset: %w", err)
	}

	dynamicClient, err := dynamic.NewForConfig(config)
	if err != nil {
		logger.Error(err, "dynamic client init failed", "config_type", configType)
		return nil, fmt.Errorf("failed to create dynamic client: %w", err)
	}

	logger.Info("kubernetes client initialized", "config_type", configType)

	return &Client{
		Clientset:     clientset,
		DynamicClient: dynamicClient,
		logger:        logger,
	}, nil
}
