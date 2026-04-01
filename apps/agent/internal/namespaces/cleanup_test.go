// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package namespaces

import (
	"context"
	"testing"

	agent "github.com/silogen/agent/internal/common"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	dynamicfake "k8s.io/client-go/dynamic/fake"
	fakeclientset "k8s.io/client-go/kubernetes/fake"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"
)

func TestCleanup_StripsNamespaceFinalizer(t *testing.T) {
	scheme := runtime.NewScheme()

	ns := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": "v1",
			"kind":       "Namespace",
			"metadata": map[string]interface{}{
				"name":       "test-ns",
				"finalizers": []interface{}{namespaceFinalizer},
			},
		},
	}

	dynamicClient := dynamicfake.NewSimpleDynamicClientWithCustomListKinds(scheme,
		map[schema.GroupVersionResource]string{
			namespaceGVR: "NamespaceList",
		},
		ns,
	)
	clientset := fakeclientset.NewSimpleClientset()
	log := zap.New()

	err := Cleanup(context.Background(), clientset, dynamicClient, log, false)
	require.NoError(t, err)

	updated, err := dynamicClient.Resource(namespaceGVR).Get(context.Background(), "test-ns", metav1.GetOptions{})
	require.NoError(t, err)
	assert.Empty(t, updated.GetFinalizers())
}

func TestCleanup_SkipsNamespaceWithoutFinalizer(t *testing.T) {
	scheme := runtime.NewScheme()

	ns := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": "v1",
			"kind":       "Namespace",
			"metadata": map[string]interface{}{
				"name": "test-ns",
			},
		},
	}

	dynamicClient := dynamicfake.NewSimpleDynamicClientWithCustomListKinds(scheme,
		map[schema.GroupVersionResource]string{
			namespaceGVR: "NamespaceList",
		},
		ns,
	)
	clientset := fakeclientset.NewSimpleClientset()
	log := zap.New()

	err := Cleanup(context.Background(), clientset, dynamicClient, log, false)
	require.NoError(t, err)

	updated, err := dynamicClient.Resource(namespaceGVR).Get(context.Background(), "test-ns", metav1.GetOptions{})
	require.NoError(t, err)
	assert.Empty(t, updated.GetFinalizers())
}

func TestCleanup_DryRunDoesNotStrip(t *testing.T) {
	scheme := runtime.NewScheme()

	ns := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": "v1",
			"kind":       "Namespace",
			"metadata": map[string]interface{}{
				"name":       "test-ns",
				"finalizers": []interface{}{namespaceFinalizer},
			},
		},
	}

	dynamicClient := dynamicfake.NewSimpleDynamicClientWithCustomListKinds(scheme,
		map[schema.GroupVersionResource]string{
			namespaceGVR: "NamespaceList",
		},
		ns,
	)
	clientset := fakeclientset.NewSimpleClientset()
	log := zap.New()

	err := Cleanup(context.Background(), clientset, dynamicClient, log, true)
	require.NoError(t, err)

	updated, err := dynamicClient.Resource(namespaceGVR).Get(context.Background(), "test-ns", metav1.GetOptions{})
	require.NoError(t, err)
	assert.Equal(t, []string{namespaceFinalizer}, updated.GetFinalizers())
}

func TestCleanup_PreservesOtherFinalizers(t *testing.T) {
	scheme := runtime.NewScheme()

	otherFinalizer := "other.io/keep-me"
	ns := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": "v1",
			"kind":       "Namespace",
			"metadata": map[string]interface{}{
				"name":       "test-ns",
				"finalizers": []interface{}{namespaceFinalizer, otherFinalizer},
			},
		},
	}

	dynamicClient := dynamicfake.NewSimpleDynamicClientWithCustomListKinds(scheme,
		map[schema.GroupVersionResource]string{
			namespaceGVR: "NamespaceList",
		},
		ns,
	)
	clientset := fakeclientset.NewSimpleClientset()
	log := zap.New()

	err := Cleanup(context.Background(), clientset, dynamicClient, log, false)
	require.NoError(t, err)

	updated, err := dynamicClient.Resource(namespaceGVR).Get(context.Background(), "test-ns", metav1.GetOptions{})
	require.NoError(t, err)
	assert.Equal(t, []string{otherFinalizer}, updated.GetFinalizers())
}

func TestCleanup_NoNamespaces(t *testing.T) {
	scheme := runtime.NewScheme()

	dynamicClient := dynamicfake.NewSimpleDynamicClientWithCustomListKinds(scheme,
		map[schema.GroupVersionResource]string{
			namespaceGVR: "NamespaceList",
		},
	)
	clientset := fakeclientset.NewSimpleClientset()
	log := zap.New()

	err := Cleanup(context.Background(), clientset, dynamicClient, log, false)
	require.NoError(t, err)
}

func TestCleanup_UsesCorrectFinalizerAndGVR(t *testing.T) {
	assert.Equal(t, "airm.silogen.ai/namespace-finalizer", namespaceFinalizer)
	assert.Equal(t, "v1", namespaceGVR.Version)
	assert.Equal(t, "namespaces", namespaceGVR.Resource)
	assert.Equal(t, agent.ProjectIDLabel, "airm.silogen.ai/project-id")
}
