// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package quotas

import (
	"context"
	"testing"

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

func TestCleanup_StripsKaiwoQueueConfigFinalizer(t *testing.T) {
	scheme := runtime.NewScheme()

	qqc := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": "kaiwo.silogen.ai/v1alpha1",
			"kind":       "KaiwoQueueConfig",
			"metadata": map[string]interface{}{
				"name":       "kaiwo",
				"finalizers": []interface{}{kaiwoQueueConfigFinalizer},
			},
		},
	}

	dynamicClient := dynamicfake.NewSimpleDynamicClientWithCustomListKinds(scheme,
		map[schema.GroupVersionResource]string{
			kaiwoQueueConfigGVR: "KaiwoQueueConfigList",
		},
		qqc,
	)

	clientset := fakeclientset.NewSimpleClientset()
	log := zap.New()

	err := Cleanup(context.Background(), clientset, dynamicClient, log, false)
	require.NoError(t, err)

	updated, err := dynamicClient.Resource(kaiwoQueueConfigGVR).Get(context.Background(), "kaiwo", metav1.GetOptions{})
	require.NoError(t, err)
	assert.Empty(t, updated.GetFinalizers())
}

func TestCleanup_DryRunDoesNotStrip(t *testing.T) {
	scheme := runtime.NewScheme()

	qqc := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": "kaiwo.silogen.ai/v1alpha1",
			"kind":       "KaiwoQueueConfig",
			"metadata": map[string]interface{}{
				"name":       "kaiwo",
				"finalizers": []interface{}{kaiwoQueueConfigFinalizer},
			},
		},
	}

	dynamicClient := dynamicfake.NewSimpleDynamicClientWithCustomListKinds(scheme,
		map[schema.GroupVersionResource]string{
			kaiwoQueueConfigGVR: "KaiwoQueueConfigList",
		},
		qqc,
	)

	clientset := fakeclientset.NewSimpleClientset()
	log := zap.New()

	err := Cleanup(context.Background(), clientset, dynamicClient, log, true)
	require.NoError(t, err)

	updated, err := dynamicClient.Resource(kaiwoQueueConfigGVR).Get(context.Background(), "kaiwo", metav1.GetOptions{})
	require.NoError(t, err)
	assert.Equal(t, []string{kaiwoQueueConfigFinalizer}, updated.GetFinalizers())
}

func TestCleanup_NoResources(t *testing.T) {
	scheme := runtime.NewScheme()

	dynamicClient := dynamicfake.NewSimpleDynamicClientWithCustomListKinds(scheme,
		map[schema.GroupVersionResource]string{
			kaiwoQueueConfigGVR: "KaiwoQueueConfigList",
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
	qqc := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": "kaiwo.silogen.ai/v1alpha1",
			"kind":       "KaiwoQueueConfig",
			"metadata": map[string]interface{}{
				"name":       "kaiwo",
				"finalizers": []interface{}{kaiwoQueueConfigFinalizer, otherFinalizer},
			},
		},
	}

	dynamicClient := dynamicfake.NewSimpleDynamicClientWithCustomListKinds(scheme,
		map[schema.GroupVersionResource]string{
			kaiwoQueueConfigGVR: "KaiwoQueueConfigList",
		},
		qqc,
	)

	clientset := fakeclientset.NewSimpleClientset()
	log := zap.New()

	err := Cleanup(context.Background(), clientset, dynamicClient, log, false)
	require.NoError(t, err)

	updated, err := dynamicClient.Resource(kaiwoQueueConfigGVR).Get(context.Background(), "kaiwo", metav1.GetOptions{})
	require.NoError(t, err)
	assert.Equal(t, []string{otherFinalizer}, updated.GetFinalizers())
}
