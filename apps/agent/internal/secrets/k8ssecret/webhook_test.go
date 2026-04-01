// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package k8ssecret

import (
	"context"
	"encoding/json"
	"net/http"
	"testing"

	agent "github.com/silogen/agent/internal/common"
	secretcommon "github.com/silogen/agent/internal/secrets/common"
	"github.com/silogen/agent/internal/testutils"
	"github.com/stretchr/testify/require"
	admissionv1 "k8s.io/api/admission/v1"
	authenticationv1 "k8s.io/api/authentication/v1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"
	"sigs.k8s.io/controller-runtime/pkg/webhook/admission"
)

type testScenario struct {
	name                string
	namespaceName       string
	projectID           string
	resourceLabels      map[string]string
	resourceAnnotations map[string]string
	oldSecretLabels     map[string]string
	expectedPatches     []testutils.ExpectedPatch
	allowed             bool
	resultMessage       string
}

func setupTestWebhook(objects ...runtime.Object) *Webhook {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)

	client := fake.NewClientBuilder().WithScheme(scheme).WithRuntimeObjects(objects...).Build()
	decoder := admission.NewDecoder(scheme)
	logger := zap.New(zap.UseDevMode(true))

	return &Webhook{
		Client:  client,
		Decoder: decoder,
		Logger:  logger,
	}
}

func createNamespace(name, projectID string) *corev1.Namespace {
	ns := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name: name,
		},
	}
	if projectID != "" {
		ns.Labels = map[string]string{
			agent.ProjectIDLabel: projectID,
		}
	}
	return ns
}

func createSecret(namespace string, labels map[string]string) *corev1.Secret {
	return &corev1.Secret{
		TypeMeta: metav1.TypeMeta{
			APIVersion: "v1",
			Kind:       "Secret",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-secret",
			Namespace: namespace,
			Labels:    labels,
		},
		Data: map[string][]byte{
			"token": []byte("secret-value"),
		},
	}
}

func createAdmissionRequest(secret *corev1.Secret, oldSecret *corev1.Secret) admission.Request {
	raw, _ := json.Marshal(secret)

	req := admission.Request{
		AdmissionRequest: admissionv1.AdmissionRequest{
			UID:       types.UID("test-uid-12345"),
			Kind:      metav1.GroupVersionKind{Group: "", Version: "v1", Kind: "Secret"},
			Namespace: secret.Namespace,
			Name:      secret.Name,
			Operation: admissionv1.Create,
			Object:    runtime.RawExtension{Raw: raw},
			UserInfo: authenticationv1.UserInfo{
				Username: "test-user@example.com",
			},
		},
	}

	if oldSecret != nil {
		oldRaw, _ := json.Marshal(oldSecret)
		req.Operation = admissionv1.Update
		req.OldObject = runtime.RawExtension{Raw: oldRaw}
	}

	return req
}

func TestSecretWebhook(t *testing.T) {
	scenarios := []testScenario{
		{
			name:           "CreateInAIRMNamespace",
			namespaceName:  "airm-test",
			projectID:      "project-123",
			resourceLabels: nil,
			expectedPatches: []testutils.ExpectedPatch{
				testutils.AddMetadataLabels(map[string]interface{}{
					agent.ProjectIDLabel:                 "project-123",
					secretcommon.ProjectSecretIDLabel:    testutils.UUIDMatcher,
					secretcommon.ProjectSecretScopeLabel: secretcommon.ProjectSecretScopeProject,
				}),
				testutils.AddMetadataAnnotations(map[string]interface{}{
					agent.AutoDiscoveredAnnotation: "true",
					agent.SubmitterAnnotation:      "test-user@example.com",
				}),
			},
			allowed: true,
		},
		{
			name:            "CreateInNonAIRMNamespace",
			namespaceName:   "regular-ns",
			projectID:       "",
			resourceLabels:  nil,
			expectedPatches: nil,
			allowed:         true,
			resultMessage:   "not managed by AIRM",
		},
		{
			name:          "PreservesExistingSecretID",
			namespaceName: "airm-test",
			projectID:     "project-123",
			resourceLabels: map[string]string{
				secretcommon.ProjectSecretIDLabel: "existing-secret-id",
			},
			expectedPatches: []testutils.ExpectedPatch{
				testutils.AddMetadataLabel(testutils.LabelSegmentProjectID, "project-123"),
				testutils.AddMetadataLabel(testutils.LabelSegmentSecretScope, secretcommon.ProjectSecretScopeProject),
				testutils.AddMetadataAnnotations(map[string]interface{}{agent.AutoDiscoveredAnnotation: "false"}),
			},
			allowed: true,
		},
		{
			name:           "UpdatePreservesIDFromOldObject",
			namespaceName:  "airm-test",
			projectID:      "project-123",
			resourceLabels: nil,
			oldSecretLabels: map[string]string{
				secretcommon.ProjectSecretIDLabel: "original-secret-id",
			},
			expectedPatches: []testutils.ExpectedPatch{
				testutils.AddMetadataLabels(map[string]interface{}{
					agent.ProjectIDLabel:                 "project-123",
					secretcommon.ProjectSecretIDLabel:    "original-secret-id",
					secretcommon.ProjectSecretScopeLabel: secretcommon.ProjectSecretScopeProject,
				}),
			},
			allowed: true,
		},
		{
			name:          "SetsProjectIDFromNamespace",
			namespaceName: "airm-test",
			projectID:     "project-from-ns",
			resourceLabels: map[string]string{
				agent.ProjectIDLabel: "wrong-project",
			},
			expectedPatches: []testutils.ExpectedPatch{
				testutils.AddMetadataLabelMatching(testutils.LabelSegmentSecretID, testutils.UUIDMatcher),
				testutils.AddMetadataLabel(testutils.LabelSegmentSecretScope, secretcommon.ProjectSecretScopeProject),
				testutils.ReplaceMetadataLabel(testutils.LabelSegmentProjectID, "project-from-ns"),
				testutils.AddMetadataAnnotations(map[string]interface{}{
					agent.AutoDiscoveredAnnotation: "true",
					agent.SubmitterAnnotation:      "test-user@example.com",
				}),
			},
			allowed: true,
		},
		{
			name:                "SubmitterAnnotation_PreservedWhenSet",
			namespaceName:       "airm-test",
			projectID:           "project-123",
			resourceLabels:      nil,
			resourceAnnotations: map[string]string{agent.SubmitterAnnotation: "aiwb-user@example.com"},
			expectedPatches: []testutils.ExpectedPatch{
				testutils.AddMetadataLabels(map[string]interface{}{
					agent.ProjectIDLabel:                 "project-123",
					secretcommon.ProjectSecretIDLabel:    testutils.UUIDMatcher,
					secretcommon.ProjectSecretScopeLabel: secretcommon.ProjectSecretScopeProject,
				}),
				testutils.AddMetadataAnnotation(testutils.AnnotationSegmentAutoDiscovered, "true"),
			},
			allowed: true,
		},
	}

	for _, s := range scenarios {
		t.Run(s.name, func(t *testing.T) {
			t.Helper()
			ns := createNamespace(s.namespaceName, s.projectID)
			webhook := setupTestWebhook(ns)

			secret := createSecret(s.namespaceName, s.resourceLabels)
			if s.resourceAnnotations != nil {
				secret.Annotations = s.resourceAnnotations
			}
			var oldSecret *corev1.Secret
			if s.oldSecretLabels != nil {
				oldSecret = createSecret(s.namespaceName, s.oldSecretLabels)
			}
			req := createAdmissionRequest(secret, oldSecret)
			resp := webhook.Handle(context.Background(), req)

			if s.resultMessage != "" {
				require.Contains(t, resp.Result.Message, s.resultMessage)
			}
			if !s.allowed {
				require.False(t, resp.Allowed)
				return
			}
			testutils.AssertWebhookResponse(t, resp.Allowed, resp.Patches, s.expectedPatches)
		})
	}
}

func TestSecretWebhook_NamespaceNotFound(t *testing.T) {
	webhook := setupTestWebhook()
	secret := createSecret("non-existent-ns", nil)
	req := createAdmissionRequest(secret, nil)
	resp := webhook.Handle(context.Background(), req)
	require.False(t, resp.Allowed)
	require.Equal(t, int32(http.StatusInternalServerError), resp.Result.Code)
}
