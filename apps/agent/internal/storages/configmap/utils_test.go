// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package configmap

import (
	"context"
	"testing"

	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/testutils"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
)

func newTestScheme() *runtime.Scheme {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)
	return scheme
}

func TestHandleDeletion_NoFinalizer(t *testing.T) {
	scheme := newTestScheme()
	now := metav1.Now()
	cm := &corev1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-cm",
			Namespace:         "test-ns",
			DeletionTimestamp: &now,
			Finalizers:        []string{"some-other-finalizer"},
			Labels: map[string]string{
				ProjectStorageIDLabel: "storage-123",
			},
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(cm).Build()
	pub := testutils.NewMockPublisher()

	err := HandleDeletion(context.Background(), c, pub, cm)

	assert.NoError(t, err)
	assert.Empty(t, pub.Published)
}

func TestHandleDeletion_PublishesAndRemovesFinalizer(t *testing.T) {
	scheme := newTestScheme()
	now := metav1.Now()
	cm := &corev1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-cm",
			Namespace:         "test-ns",
			DeletionTimestamp: &now,
			Finalizers:        []string{ConfigMapFinalizer},
			Labels: map[string]string{
				ProjectStorageIDLabel: "storage-123",
			},
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(cm).Build()
	pub := testutils.NewMockPublisher()

	err := HandleDeletion(context.Background(), c, pub, cm)

	assert.NoError(t, err)

	require.Len(t, pub.Published, 1)
	msg, ok := pub.Published[0].(*messaging.ProjectStorageUpdateMessage)
	require.True(t, ok)
	assert.Equal(t, "storage-123", msg.ProjectStorageID)
	assert.Equal(t, messaging.ConfigMapStatusDeleted, msg.Status)
	require.NotNil(t, msg.StatusReason)
	assert.Equal(t, "ConfigMap deleted.", *msg.StatusReason)

	assert.False(t, controllerutil.ContainsFinalizer(cm, ConfigMapFinalizer))
}

func TestHandleDeletion_MissingLabel_SkipsPublishAndRemovesFinalizer(t *testing.T) {
	scheme := newTestScheme()
	now := metav1.Now()
	cm := &corev1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-cm",
			Namespace:         "test-ns",
			DeletionTimestamp: &now,
			Finalizers:        []string{ConfigMapFinalizer},
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(cm).Build()
	pub := testutils.NewMockPublisher()

	err := HandleDeletion(context.Background(), c, pub, cm)

	assert.NoError(t, err)
	assert.Empty(t, pub.Published)
	assert.False(t, controllerutil.ContainsFinalizer(cm, ConfigMapFinalizer))
}

func TestHandleDeletion_PublishFails_RetainsFinalizer(t *testing.T) {
	scheme := newTestScheme()
	now := metav1.Now()
	cm := &corev1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-cm",
			Namespace:         "test-ns",
			DeletionTimestamp: &now,
			Finalizers:        []string{ConfigMapFinalizer},
			Labels: map[string]string{
				ProjectStorageIDLabel: "storage-123",
			},
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(cm).Build()
	pub := testutils.NewMockFailingPublisher(assert.AnError)

	err := HandleDeletion(context.Background(), c, pub, cm)

	assert.ErrorIs(t, err, assert.AnError)
	assert.Empty(t, pub.Published)
	assert.True(t, controllerutil.ContainsFinalizer(cm, ConfigMapFinalizer))
}

func TestHandleDeletion_BeingDeleted_NoFinalizer_NoLabel(t *testing.T) {
	scheme := newTestScheme()
	now := metav1.Now()
	cm := &corev1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-cm",
			Namespace:         "test-ns",
			DeletionTimestamp: &now,
			Finalizers:        []string{"some-other-finalizer"},
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(cm).Build()
	pub := testutils.NewMockPublisher()

	err := HandleDeletion(context.Background(), c, pub, cm)

	assert.NoError(t, err)
	assert.Empty(t, pub.Published)
}

func TestParseConfigMapManifest_Success(t *testing.T) {
	cm, err := parseConfigMapManifest(testConfigMapManifest)
	require.NoError(t, err)

	assert.Equal(t, "my-storage-info-config-map", cm.Name)
	assert.Equal(t, "test-project", cm.Namespace)
	assert.Equal(t, "storage-123", cm.Labels[ProjectStorageIDLabel])
	assert.Equal(t, "s3://my-bucket", cm.Data["BUCKET_URL"])
	assert.Equal(t, "access-key", cm.Data["ACCESS_KEY_NAME"])
	assert.Equal(t, "secret-key", cm.Data["SECRET_KEY_NAME"])
	assert.Equal(t, "my-secret", cm.Data["SECRET_NAME"])
}

func TestParseConfigMapManifest_PreservesExistingLabels(t *testing.T) {
	manifest := `
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-cm
  namespace: ns
  labels:
    app: my-app
    airm.silogen.ai/project-storage-id: "sid-123"
data:
  KEY: "value"
`

	cm, err := parseConfigMapManifest(manifest)
	require.NoError(t, err)

	assert.Equal(t, "my-app", cm.Labels["app"])
	assert.Equal(t, "sid-123", cm.Labels[ProjectStorageIDLabel])
	assert.Equal(t, "ns", cm.Namespace)
}

func TestParseConfigMapManifest_InvalidYAML(t *testing.T) {
	_, err := parseConfigMapManifest("not: valid: yaml: [")
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "failed to parse configmap manifest")
}
