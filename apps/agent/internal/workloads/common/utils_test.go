// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package common

import (
	"context"
	"testing"

	"github.com/google/uuid"
	agent "github.com/silogen/agent/internal/common"
	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/testutils"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	corev1 "k8s.io/api/core/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	apimeta "k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/client-go/discovery/cached/memory"
	discoveryfake "k8s.io/client-go/discovery/fake"
	dynamicfake "k8s.io/client-go/dynamic/fake"
	fakeclientset "k8s.io/client-go/kubernetes/fake"
	"k8s.io/client-go/restmapper"
	k8stesting "k8s.io/client-go/testing"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
)

func newScheme() *runtime.Scheme {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)
	return scheme
}

// --- HandleDeletion tests ---

func TestHandleDeletion_NoFinalizer(t *testing.T) {
	scheme := newScheme()
	now := metav1.Now()
	pod := &corev1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-pod",
			Namespace:         "test-ns",
			DeletionTimestamp: &now,
			Finalizers:        []string{"some-other-finalizer"},
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(pod).Build()
	pub := testutils.NewMockPublisher()

	err := HandleDeletion(context.Background(), c, pub, pod)

	assert.NoError(t, err)
	assert.Empty(t, pub.Published)
}

func TestHandleDeletion_PublishesAndRemovesFinalizer(t *testing.T) {
	scheme := newScheme()
	now := metav1.Now()
	workloadID := uuid.New()
	componentID := uuid.New()
	projectID := uuid.New()

	pod := &corev1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-pod",
			Namespace:         "test-ns",
			DeletionTimestamp: &now,
			Finalizers:        []string{WorkloadFinalizer},
			Labels: map[string]string{
				WorkloadIDLabel:      workloadID.String(),
				ComponentIDLabel:     componentID.String(),
				agent.ProjectIDLabel: projectID.String(),
			},
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(pod).Build()
	pub := testutils.NewMockPublisher()

	err := HandleDeletion(context.Background(), c, pub, pod)

	assert.NoError(t, err)

	require.Len(t, pub.Published, 1)
	msg, ok := pub.Published[0].(messaging.WorkloadComponentStatusMessage)
	require.True(t, ok)
	assert.Equal(t, "Deleted", msg.Status)
	assert.Equal(t, "test-pod", msg.Name)
	assert.Equal(t, workloadID.String(), msg.WorkloadID)
	assert.Equal(t, componentID.String(), msg.ID)

	assert.False(t, controllerutil.ContainsFinalizer(pod, WorkloadFinalizer))
}

func TestHandleDeletion_MissingLabels_SkipsPublishAndRemovesFinalizer(t *testing.T) {
	scheme := newScheme()
	now := metav1.Now()
	pod := &corev1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-pod",
			Namespace:         "test-ns",
			DeletionTimestamp: &now,
			Finalizers:        []string{WorkloadFinalizer},
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(pod).Build()
	pub := testutils.NewMockPublisher()

	err := HandleDeletion(context.Background(), c, pub, pod)

	assert.NoError(t, err)
	assert.Empty(t, pub.Published)
	assert.False(t, controllerutil.ContainsFinalizer(pod, WorkloadFinalizer))
}

func TestHandleDeletion_PublishFails_RetainsFinalizer(t *testing.T) {
	scheme := newScheme()
	now := metav1.Now()
	workloadID := uuid.New()
	componentID := uuid.New()
	projectID := uuid.New()

	pod := &corev1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-pod",
			Namespace:         "test-ns",
			DeletionTimestamp: &now,
			Finalizers:        []string{WorkloadFinalizer},
			Labels: map[string]string{
				WorkloadIDLabel:      workloadID.String(),
				ComponentIDLabel:     componentID.String(),
				agent.ProjectIDLabel: projectID.String(),
			},
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(pod).Build()
	pub := testutils.NewMockFailingPublisher(assert.AnError)

	err := HandleDeletion(context.Background(), c, pub, pod)

	assert.ErrorIs(t, err, assert.AnError)
	assert.Empty(t, pub.Published)
	assert.True(t, controllerutil.ContainsFinalizer(pod, WorkloadFinalizer))
}

// --- Handler utils tests ---

func TestParseDeleteWorkloadMessage(t *testing.T) {
	t.Run("valid", func(t *testing.T) {
		msg := &messaging.RawMessage{
			Type:    messaging.MessageTypeDeleteWorkload,
			Payload: []byte(`{"message_type":"delete_workload","workload_id":"11111111-1111-1111-1111-111111111111"}`),
		}
		parsed, err := ParseDeleteWorkloadMessage(msg)
		require.NoError(t, err)
		assert.Equal(t, "11111111-1111-1111-1111-111111111111", parsed.WorkloadID)
	})

	t.Run("missing workload_id", func(t *testing.T) {
		msg := &messaging.RawMessage{
			Type:    messaging.MessageTypeDeleteWorkload,
			Payload: []byte(`{"message_type":"delete_workload","workload_id":""}`),
		}
		_, err := ParseDeleteWorkloadMessage(msg)
		require.Error(t, err)
		assert.Contains(t, err.Error(), "workload_id is required")
	})

	t.Run("invalid workload_id", func(t *testing.T) {
		msg := &messaging.RawMessage{
			Type:    messaging.MessageTypeDeleteWorkload,
			Payload: []byte(`{"message_type":"delete_workload","workload_id":"not-a-uuid"}`),
		}
		_, err := ParseDeleteWorkloadMessage(msg)
		require.Error(t, err)
		assert.Contains(t, err.Error(), "invalid workload_id")
	})

	t.Run("invalid json", func(t *testing.T) {
		msg := &messaging.RawMessage{
			Type:    messaging.MessageTypeDeleteWorkload,
			Payload: []byte(`{"message_type":"delete_workload",`),
		}
		_, err := ParseDeleteWorkloadMessage(msg)
		require.Error(t, err)
		assert.Contains(t, err.Error(), "failed to parse DeleteWorkloadMessage")
	})
}

func buildRESTMapper(resources []*metav1.APIResourceList) apimeta.RESTMapper {
	clientset := fakeclientset.NewSimpleClientset()
	clientset.Discovery().(*discoveryfake.FakeDiscovery).Resources = resources
	return restmapper.NewDeferredDiscoveryRESTMapper(
		memory.NewMemCacheClient(clientset.Discovery()),
	)
}

func TestApplyObject_ReturnsAlreadyExists(t *testing.T) {
	gvr := schema.GroupVersionResource{Group: "", Version: "v1", Resource: "configmaps"}

	mapper := buildRESTMapper([]*metav1.APIResourceList{
		{
			GroupVersion: "v1",
			APIResources: []metav1.APIResource{
				{Name: "configmaps", Kind: "ConfigMap", Namespaced: true},
			},
		},
	})

	scheme := runtime.NewScheme()
	dynamicClient := dynamicfake.NewSimpleDynamicClientWithCustomListKinds(scheme,
		map[schema.GroupVersionResource]string{gvr: "ConfigMapList"},
	)
	dynamicClient.PrependReactor("create", "configmaps", func(action k8stesting.Action) (bool, runtime.Object, error) {
		return true, nil, apierrors.NewAlreadyExists(schema.GroupResource{Resource: "configmaps"}, "cm-a")
	})

	obj := &unstructured.Unstructured{Object: map[string]interface{}{
		"apiVersion": "v1",
		"kind":       KindConfigMap,
		"metadata": map[string]interface{}{
			"name":      "cm-a",
			"namespace": "ns1",
		},
	}}
	obj.SetGroupVersionKind(schema.FromAPIVersionAndKind("v1", KindConfigMap))

	err := ApplyObject(context.Background(), dynamicClient, mapper, obj)
	require.Error(t, err)
	require.True(t, apierrors.IsAlreadyExists(err), "expected AlreadyExists error, got: %v", err)
}
