// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package common

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

const testFinalizer = "airm.silogen.ai/test-finalizer"

func newScheme() *runtime.Scheme {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)
	return scheme
}

func TestBuildLabelSelector(t *testing.T) {
	got := BuildLabelSelector("123")
	want := ProjectSecretIDLabel + "=123"
	if got != want {
		t.Fatalf("expected %q, got %q", want, got)
	}
}

func strPtr(s string) *string { return &s }

func TestGetSecretUseCaseFromLabels(t *testing.T) {
	tests := []struct {
		name     string
		labels   map[string]string
		expected *string
	}{
		{
			name:     "nil labels",
			labels:   nil,
			expected: nil,
		},
		{
			name:     "no use-case label",
			labels:   map[string]string{},
			expected: nil,
		},
		{
			name:     "empty use-case label",
			labels:   map[string]string{UseCaseLabel: ""},
			expected: nil,
		},
		{
			name:     "HuggingFace canonical casing",
			labels:   map[string]string{UseCaseLabel: "HuggingFace"},
			expected: strPtr("HuggingFace"),
		},
		{
			name:     "HuggingFace all lowercase",
			labels:   map[string]string{UseCaseLabel: "huggingface"},
			expected: strPtr("HuggingFace"),
		},
		{
			name:     "HuggingFace all uppercase",
			labels:   map[string]string{UseCaseLabel: "HUGGINGFACE"},
			expected: strPtr("HuggingFace"),
		},
		{
			name:     "S3 lowercase",
			labels:   map[string]string{UseCaseLabel: "s3"},
			expected: strPtr("S3"),
		},
		{
			name:     "Generic mixed case",
			labels:   map[string]string{UseCaseLabel: "generic"},
			expected: strPtr("Generic"),
		},
		{
			name:     "Database uppercase",
			labels:   map[string]string{UseCaseLabel: "DATABASE"},
			expected: strPtr("Database"),
		},
		{
			name:     "ImagePullSecret lowercase",
			labels:   map[string]string{UseCaseLabel: "imagepullsecret"},
			expected: strPtr("ImagePullSecret"),
		},
		{
			name:     "unrecognized value passed through as-is",
			labels:   map[string]string{UseCaseLabel: "CustomUseCase"},
			expected: strPtr("CustomUseCase"),
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := GetSecretUseCaseFromLabels(tt.labels)
			if tt.expected == nil {
				assert.Nil(t, got)
				return
			}
			require.NotNil(t, got)
			assert.Equal(t, *tt.expected, *got)
		})
	}
}

func TestGetSecretScopeFromLabels(t *testing.T) {
	tests := []struct {
		name     string
		labels   map[string]string
		expected *messaging.SecretScope
	}{
		{
			name:     "nil labels",
			labels:   nil,
			expected: nil,
		},
		{
			name:     "no scope label",
			labels:   map[string]string{},
			expected: nil,
		},
		{
			name: "project scope lowercase",
			labels: map[string]string{
				ProjectSecretScopeLabel: "project",
			},
			expected: func() *messaging.SecretScope {
				s := messaging.SecretScopeProject
				return &s
			}(),
		},
		{
			name: "project scope title case",
			labels: map[string]string{
				ProjectSecretScopeLabel: "Project",
			},
			expected: func() *messaging.SecretScope {
				s := messaging.SecretScopeProject
				return &s
			}(),
		},
		{
			name: "organization scope lowercase",
			labels: map[string]string{
				ProjectSecretScopeLabel: "organization",
			},
			expected: func() *messaging.SecretScope {
				s := messaging.SecretScopeOrganization
				return &s
			}(),
		},
		{
			name: "organization scope title case",
			labels: map[string]string{
				ProjectSecretScopeLabel: "Organization",
			},
			expected: func() *messaging.SecretScope {
				s := messaging.SecretScopeOrganization
				return &s
			}(),
		},
		{
			name: "invalid scope",
			labels: map[string]string{
				ProjectSecretScopeLabel: "invalid",
			},
			expected: nil,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := GetSecretScopeFromLabels(tt.labels)
			if tt.expected == nil {
				assert.Nil(t, got)
				return
			}
			require.NotNil(t, got)
			assert.Equal(t, *tt.expected, *got)
		})
	}
}

func TestHandleDeletion_NoFinalizer(t *testing.T) {
	scheme := newScheme()
	now := metav1.Now()
	secret := &corev1.Secret{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-secret",
			Namespace:         "test-ns",
			DeletionTimestamp: &now,
			Finalizers:        []string{"some-other-finalizer"},
			Labels: map[string]string{
				ProjectSecretIDLabel: "secret-123",
			},
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(secret).Build()
	pub := testutils.NewMockPublisher()

	err := HandleDeletion(context.Background(), c, pub, secret, testFinalizer, "deleted")

	assert.NoError(t, err)
	assert.Empty(t, pub.Published)
}

func TestHandleDeletion_PublishesAndRemovesFinalizer(t *testing.T) {
	scheme := newScheme()
	now := metav1.Now()
	secret := &corev1.Secret{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-secret",
			Namespace:         "test-ns",
			DeletionTimestamp: &now,
			Finalizers:        []string{testFinalizer},
			Labels: map[string]string{
				ProjectSecretIDLabel:    "secret-123",
				ProjectSecretScopeLabel: "project",
			},
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(secret).Build()
	pub := testutils.NewMockPublisher()

	err := HandleDeletion(context.Background(), c, pub, secret, testFinalizer, "Secret deleted successfully")

	assert.NoError(t, err)

	require.Len(t, pub.Published, 1)
	msg, ok := pub.Published[0].(*messaging.ProjectSecretsUpdateMessage)
	require.True(t, ok)
	assert.Equal(t, "secret-123", msg.ProjectSecretID)
	assert.Equal(t, messaging.ProjectSecretStatusDeleted, msg.Status)
	require.NotNil(t, msg.StatusReason)
	assert.Equal(t, "Secret deleted successfully", *msg.StatusReason)
	require.NotNil(t, msg.SecretScope)
	assert.Equal(t, messaging.SecretScopeProject, *msg.SecretScope)

	assert.False(t, controllerutil.ContainsFinalizer(secret, testFinalizer))
}

func TestHandleDeletion_MissingLabel_SkipsPublishAndRemovesFinalizer(t *testing.T) {
	scheme := newScheme()
	now := metav1.Now()
	secret := &corev1.Secret{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-secret",
			Namespace:         "test-ns",
			DeletionTimestamp: &now,
			Finalizers:        []string{testFinalizer},
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(secret).Build()
	pub := testutils.NewMockPublisher()

	err := HandleDeletion(context.Background(), c, pub, secret, testFinalizer, "deleted")

	assert.NoError(t, err)
	assert.Empty(t, pub.Published)
	assert.False(t, controllerutil.ContainsFinalizer(secret, testFinalizer))
}

func TestHandleDeletion_PublishFails_RetainsFinalizer(t *testing.T) {
	scheme := newScheme()
	now := metav1.Now()
	secret := &corev1.Secret{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-secret",
			Namespace:         "test-ns",
			DeletionTimestamp: &now,
			Finalizers:        []string{testFinalizer},
			Labels: map[string]string{
				ProjectSecretIDLabel: "secret-123",
			},
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(secret).Build()
	pub := testutils.NewMockFailingPublisher(assert.AnError)

	err := HandleDeletion(context.Background(), c, pub, secret, testFinalizer, "deleted")

	assert.ErrorIs(t, err, assert.AnError)
	assert.Empty(t, pub.Published)
	assert.True(t, controllerutil.ContainsFinalizer(secret, testFinalizer))
}

func TestHandleDeletion_WithoutScope(t *testing.T) {
	scheme := newScheme()
	now := metav1.Now()
	secret := &corev1.Secret{
		ObjectMeta: metav1.ObjectMeta{
			Name:              "test-secret",
			Namespace:         "test-ns",
			DeletionTimestamp: &now,
			Finalizers:        []string{testFinalizer},
			Labels: map[string]string{
				ProjectSecretIDLabel: "secret-456",
			},
		},
	}

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(secret).Build()
	pub := testutils.NewMockPublisher()

	err := HandleDeletion(context.Background(), c, pub, secret, testFinalizer, "Secret deleted successfully")

	assert.NoError(t, err)

	require.Len(t, pub.Published, 1)
	msg, ok := pub.Published[0].(*messaging.ProjectSecretsUpdateMessage)
	require.True(t, ok)
	assert.Equal(t, "secret-456", msg.ProjectSecretID)
	assert.Equal(t, messaging.ProjectSecretStatusDeleted, msg.Status)
	assert.Nil(t, msg.SecretScope)

	assert.False(t, controllerutil.ContainsFinalizer(secret, testFinalizer))
}
