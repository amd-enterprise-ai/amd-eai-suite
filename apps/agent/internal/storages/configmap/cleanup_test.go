// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package configmap

import (
	"context"
	"testing"

	agent "github.com/silogen/agent/internal/common"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	dynamicfake "k8s.io/client-go/dynamic/fake"
	fakeclientset "k8s.io/client-go/kubernetes/fake"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"
)

func managedNamespace(name string) *corev1.Namespace {
	return &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name:   name,
			Labels: map[string]string{agent.ProjectIDLabel: "test-project"},
		},
	}
}

func TestCleanup_StripsConfigMapFinalizer(t *testing.T) {
	scheme := runtime.NewScheme()

	cm := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": "v1",
			"kind":       "ConfigMap",
			"metadata": map[string]interface{}{
				"name":       "test-cm",
				"namespace":  "managed-ns",
				"finalizers": []interface{}{ConfigMapFinalizer},
			},
		},
	}

	dynamicClient := dynamicfake.NewSimpleDynamicClientWithCustomListKinds(scheme,
		map[schema.GroupVersionResource]string{
			configMapGVR: "ConfigMapList",
		},
		cm,
	)

	clientset := fakeclientset.NewSimpleClientset(managedNamespace("managed-ns"))
	log := zap.New()

	err := Cleanup(context.Background(), clientset, dynamicClient, log, false)
	require.NoError(t, err)

	updated, err := dynamicClient.Resource(configMapGVR).Namespace("managed-ns").Get(context.Background(), "test-cm", metav1.GetOptions{})
	require.NoError(t, err)
	assert.Empty(t, updated.GetFinalizers())
}

func TestCleanup_DryRunDoesNotStrip(t *testing.T) {
	scheme := runtime.NewScheme()

	cm := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": "v1",
			"kind":       "ConfigMap",
			"metadata": map[string]interface{}{
				"name":       "test-cm",
				"namespace":  "managed-ns",
				"finalizers": []interface{}{ConfigMapFinalizer},
			},
		},
	}

	dynamicClient := dynamicfake.NewSimpleDynamicClientWithCustomListKinds(scheme,
		map[schema.GroupVersionResource]string{
			configMapGVR: "ConfigMapList",
		},
		cm,
	)

	clientset := fakeclientset.NewSimpleClientset(managedNamespace("managed-ns"))
	log := zap.New()

	err := Cleanup(context.Background(), clientset, dynamicClient, log, true)
	require.NoError(t, err)

	updated, err := dynamicClient.Resource(configMapGVR).Namespace("managed-ns").Get(context.Background(), "test-cm", metav1.GetOptions{})
	require.NoError(t, err)
	assert.Equal(t, []string{ConfigMapFinalizer}, updated.GetFinalizers())
}

func TestCleanup_NoManagedNamespaces(t *testing.T) {
	scheme := runtime.NewScheme()

	dynamicClient := dynamicfake.NewSimpleDynamicClientWithCustomListKinds(scheme,
		map[schema.GroupVersionResource]string{
			configMapGVR: "ConfigMapList",
		},
	)

	clientset := fakeclientset.NewSimpleClientset()
	log := zap.New()

	err := Cleanup(context.Background(), clientset, dynamicClient, log, false)
	require.NoError(t, err)
}

func TestCleanup_PreservesOtherFinalizers(t *testing.T) {
	scheme := runtime.NewScheme()

	otherFinalizer := "other.io/keep-me"
	cm := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": "v1",
			"kind":       "ConfigMap",
			"metadata": map[string]interface{}{
				"name":       "test-cm",
				"namespace":  "managed-ns",
				"finalizers": []interface{}{ConfigMapFinalizer, otherFinalizer},
			},
		},
	}

	dynamicClient := dynamicfake.NewSimpleDynamicClientWithCustomListKinds(scheme,
		map[schema.GroupVersionResource]string{
			configMapGVR: "ConfigMapList",
		},
		cm,
	)

	clientset := fakeclientset.NewSimpleClientset(managedNamespace("managed-ns"))
	log := zap.New()

	err := Cleanup(context.Background(), clientset, dynamicClient, log, false)
	require.NoError(t, err)

	updated, err := dynamicClient.Resource(configMapGVR).Namespace("managed-ns").Get(context.Background(), "test-cm", metav1.GetOptions{})
	require.NoError(t, err)
	assert.Equal(t, []string{otherFinalizer}, updated.GetFinalizers())
}

func TestCleanup_MultipleNamespaces(t *testing.T) {
	scheme := runtime.NewScheme()

	cm1 := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": "v1",
			"kind":       "ConfigMap",
			"metadata": map[string]interface{}{
				"name":       "cm-1",
				"namespace":  "ns-a",
				"finalizers": []interface{}{ConfigMapFinalizer},
			},
		},
	}
	cm2 := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": "v1",
			"kind":       "ConfigMap",
			"metadata": map[string]interface{}{
				"name":       "cm-2",
				"namespace":  "ns-b",
				"finalizers": []interface{}{ConfigMapFinalizer},
			},
		},
	}

	dynamicClient := dynamicfake.NewSimpleDynamicClientWithCustomListKinds(scheme,
		map[schema.GroupVersionResource]string{
			configMapGVR: "ConfigMapList",
		},
		cm1, cm2,
	)

	clientset := fakeclientset.NewSimpleClientset(managedNamespace("ns-a"), managedNamespace("ns-b"))
	log := zap.New()

	err := Cleanup(context.Background(), clientset, dynamicClient, log, false)
	require.NoError(t, err)

	updated1, err := dynamicClient.Resource(configMapGVR).Namespace("ns-a").Get(context.Background(), "cm-1", metav1.GetOptions{})
	require.NoError(t, err)
	assert.Empty(t, updated1.GetFinalizers())

	updated2, err := dynamicClient.Resource(configMapGVR).Namespace("ns-b").Get(context.Background(), "cm-2", metav1.GetOptions{})
	require.NoError(t, err)
	assert.Empty(t, updated2.GetFinalizers())
}
