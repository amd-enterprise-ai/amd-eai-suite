// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package workloads

import (
	"context"
	"testing"

	agent "github.com/silogen/agent/internal/common"
	common "github.com/silogen/agent/internal/workloads/common"
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

func newManagedNamespace() *corev1.Namespace {
	return &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name:   "managed-ns",
			Labels: map[string]string{agent.ProjectIDLabel: "test-project"},
		},
	}
}

func TestCleanup_StripsFinalizerFromDeployment(t *testing.T) {
	scheme := runtime.NewScheme()

	gvr := schema.GroupVersionResource{Group: "apps", Version: "v1", Resource: "deployments"}

	dep := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": "apps/v1",
			"kind":       "Deployment",
			"metadata": map[string]interface{}{
				"name":       "test-dep",
				"namespace":  "managed-ns",
				"finalizers": []interface{}{common.WorkloadFinalizer},
			},
		},
	}

	dynamicClient := dynamicfake.NewSimpleDynamicClientWithCustomListKinds(scheme,
		map[schema.GroupVersionResource]string{
			gvr: "DeploymentList",
		},
		dep,
	)

	clientset := fakeclientset.NewSimpleClientset(newManagedNamespace())
	clientset.Discovery().(*discoveryfake.FakeDiscovery).Resources = []*metav1.APIResourceList{
		{
			GroupVersion: "apps/v1",
			APIResources: []metav1.APIResource{
				{Name: "deployments", Kind: "Deployment", Namespaced: true},
			},
		},
	}

	log := zap.New()

	err := Cleanup(context.Background(), clientset, dynamicClient, log, false)
	require.NoError(t, err)

	updated, err := dynamicClient.Resource(gvr).Namespace("managed-ns").Get(context.Background(), "test-dep", metav1.GetOptions{})
	require.NoError(t, err)
	assert.Empty(t, updated.GetFinalizers())
}

func TestCleanup_SkipsUninstalledCRDs(t *testing.T) {
	scheme := runtime.NewScheme()

	clientset := fakeclientset.NewSimpleClientset(newManagedNamespace())
	// Only register core resources — CRDs like KaiwoJob, HTTPRoute are absent
	clientset.Discovery().(*discoveryfake.FakeDiscovery).Resources = []*metav1.APIResourceList{
		{
			GroupVersion: "v1",
			APIResources: []metav1.APIResource{
				{Name: "configmaps", Kind: "ConfigMap", Namespaced: true},
				{Name: "services", Kind: "Service", Namespaced: true},
				{Name: "pods", Kind: "Pod", Namespaced: true},
			},
		},
		{
			GroupVersion: "apps/v1",
			APIResources: []metav1.APIResource{
				{Name: "deployments", Kind: "Deployment", Namespaced: true},
				{Name: "statefulsets", Kind: "StatefulSet", Namespaced: true},
				{Name: "daemonsets", Kind: "DaemonSet", Namespaced: true},
				{Name: "replicasets", Kind: "ReplicaSet", Namespaced: true},
			},
		},
		{
			GroupVersion: "batch/v1",
			APIResources: []metav1.APIResource{
				{Name: "jobs", Kind: "Job", Namespaced: true},
				{Name: "cronjobs", Kind: "CronJob", Namespaced: true},
			},
		},
		{
			GroupVersion: "networking.k8s.io/v1",
			APIResources: []metav1.APIResource{
				{Name: "ingresses", Kind: "Ingress", Namespaced: true},
			},
		},
	}

	// Dynamic client needs all discoverable GVRs registered
	dynamicClient := dynamicfake.NewSimpleDynamicClientWithCustomListKinds(scheme,
		map[schema.GroupVersionResource]string{
			{Version: "v1", Resource: "configmaps"}:                            "ConfigMapList",
			{Version: "v1", Resource: "services"}:                              "ServiceList",
			{Version: "v1", Resource: "pods"}:                                  "PodList",
			{Group: "apps", Version: "v1", Resource: "deployments"}:            "DeploymentList",
			{Group: "apps", Version: "v1", Resource: "statefulsets"}:           "StatefulSetList",
			{Group: "apps", Version: "v1", Resource: "daemonsets"}:             "DaemonSetList",
			{Group: "apps", Version: "v1", Resource: "replicasets"}:            "ReplicaSetList",
			{Group: "batch", Version: "v1", Resource: "jobs"}:                  "JobList",
			{Group: "batch", Version: "v1", Resource: "cronjobs"}:              "CronJobList",
			{Group: "networking.k8s.io", Version: "v1", Resource: "ingresses"}: "IngressList",
		},
	)
	log := zap.New()

	err := Cleanup(context.Background(), clientset, dynamicClient, log, false)
	require.NoError(t, err)
}

func TestCleanup_DryRunDoesNotStrip(t *testing.T) {
	scheme := runtime.NewScheme()

	gvr := schema.GroupVersionResource{Group: "apps", Version: "v1", Resource: "deployments"}

	dep := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": "apps/v1",
			"kind":       "Deployment",
			"metadata": map[string]interface{}{
				"name":       "test-dep",
				"namespace":  "managed-ns",
				"finalizers": []interface{}{common.WorkloadFinalizer},
			},
		},
	}

	dynamicClient := dynamicfake.NewSimpleDynamicClientWithCustomListKinds(scheme,
		map[schema.GroupVersionResource]string{
			gvr: "DeploymentList",
		},
		dep,
	)

	clientset := fakeclientset.NewSimpleClientset(newManagedNamespace())
	clientset.Discovery().(*discoveryfake.FakeDiscovery).Resources = []*metav1.APIResourceList{
		{
			GroupVersion: "apps/v1",
			APIResources: []metav1.APIResource{
				{Name: "deployments", Kind: "Deployment", Namespaced: true},
			},
		},
	}

	log := zap.New()

	err := Cleanup(context.Background(), clientset, dynamicClient, log, true)
	require.NoError(t, err)

	updated, err := dynamicClient.Resource(gvr).Namespace("managed-ns").Get(context.Background(), "test-dep", metav1.GetOptions{})
	require.NoError(t, err)
	assert.Equal(t, []string{common.WorkloadFinalizer}, updated.GetFinalizers())
}

func TestCleanup_NoManagedNamespaces(t *testing.T) {
	scheme := runtime.NewScheme()

	clientset := fakeclientset.NewSimpleClientset()
	clientset.Discovery().(*discoveryfake.FakeDiscovery).Resources = []*metav1.APIResourceList{
		{
			GroupVersion: "apps/v1",
			APIResources: []metav1.APIResource{
				{Name: "deployments", Kind: "Deployment", Namespaced: true},
			},
		},
	}

	dynamicClient := dynamicfake.NewSimpleDynamicClient(scheme)
	log := zap.New()

	err := Cleanup(context.Background(), clientset, dynamicClient, log, false)
	require.NoError(t, err)
}

func TestCleanup_PreservesOtherFinalizers(t *testing.T) {
	scheme := runtime.NewScheme()

	gvr := schema.GroupVersionResource{Group: "apps", Version: "v1", Resource: "deployments"}
	otherFinalizer := "other.io/keep-me"

	dep := &unstructured.Unstructured{
		Object: map[string]interface{}{
			"apiVersion": "apps/v1",
			"kind":       "Deployment",
			"metadata": map[string]interface{}{
				"name":       "test-dep",
				"namespace":  "managed-ns",
				"finalizers": []interface{}{common.WorkloadFinalizer, otherFinalizer},
			},
		},
	}

	dynamicClient := dynamicfake.NewSimpleDynamicClientWithCustomListKinds(scheme,
		map[schema.GroupVersionResource]string{
			gvr: "DeploymentList",
		},
		dep,
	)

	clientset := fakeclientset.NewSimpleClientset(newManagedNamespace())
	clientset.Discovery().(*discoveryfake.FakeDiscovery).Resources = []*metav1.APIResourceList{
		{
			GroupVersion: "apps/v1",
			APIResources: []metav1.APIResource{
				{Name: "deployments", Kind: "Deployment", Namespaced: true},
			},
		},
	}

	log := zap.New()

	err := Cleanup(context.Background(), clientset, dynamicClient, log, false)
	require.NoError(t, err)

	updated, err := dynamicClient.Resource(gvr).Namespace("managed-ns").Get(context.Background(), "test-dep", metav1.GetOptions{})
	require.NoError(t, err)
	assert.Equal(t, []string{otherFinalizer}, updated.GetFinalizers())
}
