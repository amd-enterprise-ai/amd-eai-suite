// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package workloads

import (
	"context"
	"fmt"
	"testing"

	agent "github.com/silogen/agent/internal/common"
	"github.com/silogen/agent/internal/messaging"
	common "github.com/silogen/agent/internal/workloads/common"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/client-go/discovery/cached/memory"
	discoveryfake "k8s.io/client-go/discovery/fake"
	dynamicfake "k8s.io/client-go/dynamic/fake"
	"k8s.io/client-go/kubernetes"
	fakeclientset "k8s.io/client-go/kubernetes/fake"
	"k8s.io/client-go/restmapper"
	k8stesting "k8s.io/client-go/testing"
)

func buildRESTMapper(clientset kubernetes.Interface) apimeta.RESTMapper {
	return restmapper.NewDeferredDiscoveryRESTMapper(
		memory.NewMemCacheClient(clientset.Discovery()),
	)
}

func TestDeleteKnownWorkloadComponents_PublishesDeleteFailed(t *testing.T) {
	orig := KnownComponentGroupKinds
	KnownComponentGroupKinds = []schema.GroupKind{{Group: "", Kind: common.KindConfigMap}}
	t.Cleanup(func() { KnownComponentGroupKinds = orig })

	gvr := schema.GroupVersionResource{Group: "", Version: "v1", Resource: "configmaps"}

	workloadID := "11111111-1111-1111-1111-111111111111"
	cid1 := "22222222-2222-2222-2222-222222222222"
	cid2 := "33333333-3333-3333-3333-333333333333"
	projectID := "44444444-4444-4444-4444-444444444444"

	cm1 := &unstructured.Unstructured{Object: map[string]interface{}{
		"apiVersion": "v1",
		"kind":       common.KindConfigMap,
		"metadata": map[string]interface{}{
			"name":      "cm-a",
			"namespace": "ns1",
			"labels": map[string]interface{}{
				common.WorkloadIDLabel:  workloadID,
				common.ComponentIDLabel: cid1,
				agent.ProjectIDLabel:    projectID,
			},
		},
	}}
	cm2 := &unstructured.Unstructured{Object: map[string]interface{}{
		"apiVersion": "v1",
		"kind":       common.KindConfigMap,
		"metadata": map[string]interface{}{
			"name":      "cm-b",
			"namespace": "ns1",
			"labels": map[string]interface{}{
				common.WorkloadIDLabel:  workloadID,
				common.ComponentIDLabel: cid2,
				agent.ProjectIDLabel:    projectID,
			},
		},
	}}

	scheme := runtime.NewScheme()
	dynamicClient := dynamicfake.NewSimpleDynamicClientWithCustomListKinds(scheme,
		map[schema.GroupVersionResource]string{gvr: "ConfigMapList"},
		cm1, cm2,
	)

	dynamicClient.PrependReactor("delete", "configmaps", func(action k8stesting.Action) (bool, runtime.Object, error) {
		da := action.(k8stesting.DeleteAction)
		switch da.GetName() {
		case "cm-a":
			return true, nil, fmt.Errorf("boom")
		case "cm-b":
			return true, nil, apierrors.NewNotFound(schema.GroupResource{Resource: "configmaps"}, "cm-b")
		}
		return false, nil, nil
	})

	clientset := fakeclientset.NewSimpleClientset()
	clientset.Discovery().(*discoveryfake.FakeDiscovery).Resources = []*metav1.APIResourceList{
		{
			GroupVersion: "v1",
			APIResources: []metav1.APIResource{
				{Name: "configmaps", Kind: "ConfigMap", Namespaced: true},
			},
		},
	}

	mapper := buildRESTMapper(clientset)
	pub := &mockPublisher{}

	deleted := DeleteKnownWorkloadComponents(
		context.Background(),
		dynamicClient,
		mapper,
		pub,
		common.WorkloadIDLabelSelector(workloadID),
	)
	assert.Equal(t, 2, deleted)

	require.Len(t, pub.published, 1)
	msg, ok := pub.published[0].(*messaging.WorkloadComponentStatusMessage)
	require.True(t, ok, "expected WorkloadComponentStatusMessage, got %T", pub.published[0])
	assert.Equal(t, messaging.MessageTypeWorkloadComponentStatusUpdate, msg.MessageType)
	assert.Equal(t, cid1, msg.ID)
	assert.Equal(t, "cm-a", msg.Name)
	assert.Equal(t, messaging.WorkloadComponentKindConfigMap, msg.Kind)
	assert.Equal(t, workloadID, msg.WorkloadID)
	assert.Equal(t, "DeleteFailed", msg.Status)
	require.NotNil(t, msg.StatusReason)
	assert.Contains(t, *msg.StatusReason, "boom")
}
