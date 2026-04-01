// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package secrets

import (
	"context"
	"testing"

	agent "github.com/silogen/agent/internal/common"
	secretscommon "github.com/silogen/agent/internal/secrets/common"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	discoveryfake "k8s.io/client-go/discovery/fake"
	dynamicfake "k8s.io/client-go/dynamic/fake"
	fakeclientset "k8s.io/client-go/kubernetes/fake"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"
)

var (
	secretGVR         = schema.GroupVersionResource{Version: "v1", Resource: "secrets"}
	externalSecretGVR = schema.GroupVersionResource{Group: "external-secrets.io", Version: "v1beta1", Resource: "externalsecrets"}

	secretGVRListKinds = map[schema.GroupVersionResource]string{
		secretGVR:         "SecretList",
		externalSecretGVR: "ExternalSecretList",
	}

	fakeAPIResources = []*metav1.APIResourceList{
		{
			GroupVersion: "v1",
			APIResources: []metav1.APIResource{
				{Name: "secrets", Kind: "Secret", Namespaced: true},
			},
		},
		{
			GroupVersion: externalSecretGVR.Group + "/" + externalSecretGVR.Version,
			APIResources: []metav1.APIResource{
				{Name: "externalsecrets", Kind: "ExternalSecret", Namespaced: true},
			},
		},
	}
)

func newManagedNamespace() *corev1.Namespace {
	return &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name:   "managed-ns",
			Labels: map[string]string{agent.ProjectIDLabel: "test-project"},
		},
	}
}

func TestCleanup_StripsFinalizer(t *testing.T) {
	tests := []struct {
		name       string
		apiVersion string
		kind       string
		objName    string
		gvr        schema.GroupVersionResource
	}{
		{"k8s secret", "v1", "Secret", "test-secret", secretGVR},
		{"external secret", externalSecretGVR.Group + "/" + externalSecretGVR.Version, "ExternalSecret", "test-es", externalSecretGVR},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			obj := &unstructured.Unstructured{
				Object: map[string]interface{}{
					"apiVersion": tt.apiVersion,
					"kind":       tt.kind,
					"metadata": map[string]interface{}{
						"name":       tt.objName,
						"namespace":  "managed-ns",
						"finalizers": []interface{}{secretscommon.SecretFinalizer},
					},
				},
			}

			dynamicClient := dynamicfake.NewSimpleDynamicClientWithCustomListKinds(
				runtime.NewScheme(), secretGVRListKinds, obj,
			)
			clientset := fakeclientset.NewSimpleClientset(newManagedNamespace())
			clientset.Discovery().(*discoveryfake.FakeDiscovery).Resources = fakeAPIResources

			err := Cleanup(context.Background(), clientset, dynamicClient, zap.New(), false)
			require.NoError(t, err)

			updated, err := dynamicClient.Resource(tt.gvr).Namespace("managed-ns").Get(
				context.Background(), tt.objName, metav1.GetOptions{})
			require.NoError(t, err)
			assert.Empty(t, updated.GetFinalizers())
		})
	}
}

func TestCleanup_DryRunDoesNotStrip(t *testing.T) {
	secret := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": "v1",
			"kind":       "Secret",
			"metadata": map[string]interface{}{
				"name":       "test-secret",
				"namespace":  "managed-ns",
				"finalizers": []interface{}{secretscommon.SecretFinalizer},
			},
		},
	}

	dynamicClient := dynamicfake.NewSimpleDynamicClientWithCustomListKinds(
		runtime.NewScheme(), secretGVRListKinds, secret,
	)
	clientset := fakeclientset.NewSimpleClientset(newManagedNamespace())
	clientset.Discovery().(*discoveryfake.FakeDiscovery).Resources = fakeAPIResources

	err := Cleanup(context.Background(), clientset, dynamicClient, zap.New(), true)
	require.NoError(t, err)

	updated, err := dynamicClient.Resource(secretGVR).Namespace("managed-ns").Get(
		context.Background(), "test-secret", metav1.GetOptions{})
	require.NoError(t, err)
	assert.Equal(t, []string{secretscommon.SecretFinalizer}, updated.GetFinalizers())
}

func TestCleanup_NoManagedNamespaces(t *testing.T) {
	dynamicClient := dynamicfake.NewSimpleDynamicClientWithCustomListKinds(
		runtime.NewScheme(), secretGVRListKinds,
	)
	clientset := fakeclientset.NewSimpleClientset()
	clientset.Discovery().(*discoveryfake.FakeDiscovery).Resources = fakeAPIResources

	err := Cleanup(context.Background(), clientset, dynamicClient, zap.New(), false)
	require.NoError(t, err)
}

func TestCleanup_SkipsUninstalledExternalSecrets(t *testing.T) {
	secret := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": "v1",
			"kind":       "Secret",
			"metadata": map[string]interface{}{
				"name":       "test-secret",
				"namespace":  "managed-ns",
				"finalizers": []interface{}{secretscommon.SecretFinalizer},
			},
		},
	}

	dynamicClient := dynamicfake.NewSimpleDynamicClientWithCustomListKinds(
		runtime.NewScheme(), secretGVRListKinds, secret,
	)
	clientset := fakeclientset.NewSimpleClientset(newManagedNamespace())
	// Only core resources — ExternalSecret CRD is absent
	clientset.Discovery().(*discoveryfake.FakeDiscovery).Resources = []*metav1.APIResourceList{
		{
			GroupVersion: "v1",
			APIResources: []metav1.APIResource{
				{Name: "secrets", Kind: "Secret", Namespaced: true},
			},
		},
	}

	err := Cleanup(context.Background(), clientset, dynamicClient, zap.New(), false)
	require.NoError(t, err)

	updated, err := dynamicClient.Resource(secretGVR).Namespace("managed-ns").Get(
		context.Background(), "test-secret", metav1.GetOptions{})
	require.NoError(t, err)
	assert.Empty(t, updated.GetFinalizers())
}

func TestCleanup_PreservesOtherFinalizers(t *testing.T) {
	otherFinalizer := "other.io/keep-me"
	secret := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": "v1",
			"kind":       "Secret",
			"metadata": map[string]interface{}{
				"name":       "test-secret",
				"namespace":  "managed-ns",
				"finalizers": []interface{}{secretscommon.SecretFinalizer, otherFinalizer},
			},
		},
	}

	dynamicClient := dynamicfake.NewSimpleDynamicClientWithCustomListKinds(
		runtime.NewScheme(), secretGVRListKinds, secret,
	)
	clientset := fakeclientset.NewSimpleClientset(newManagedNamespace())
	clientset.Discovery().(*discoveryfake.FakeDiscovery).Resources = fakeAPIResources

	err := Cleanup(context.Background(), clientset, dynamicClient, zap.New(), false)
	require.NoError(t, err)

	updated, err := dynamicClient.Resource(secretGVR).Namespace("managed-ns").Get(
		context.Background(), "test-secret", metav1.GetOptions{})
	require.NoError(t, err)
	assert.Equal(t, []string{otherFinalizer}, updated.GetFinalizers())
}
