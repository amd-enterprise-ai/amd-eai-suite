// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package replicaset

import (
	"context"
	"encoding/json"
	"net/http"
	"testing"

	agent "github.com/silogen/agent/internal/common"
	"github.com/silogen/agent/internal/testutils"
	"github.com/stretchr/testify/require"
	admissionv1 "k8s.io/api/admission/v1"
	appsv1 "k8s.io/api/apps/v1"
	authenticationv1 "k8s.io/api/authentication/v1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"
	"sigs.k8s.io/controller-runtime/pkg/webhook/admission"

	"github.com/silogen/agent/internal/workloads/common"
)

type testScenario struct {
	name                string
	namespaceName       string
	projectID           string
	resourceLabels      map[string]string
	resourceAnnotations map[string]string
	oldRSLabels         map[string]string
	expectedPatches     []testutils.ExpectedPatch
	allowed             bool
	resultMessage       string
}

func setupTestWebhook(objects ...runtime.Object) *Webhook {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)
	_ = appsv1.AddToScheme(scheme)

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
		ObjectMeta: metav1.ObjectMeta{Name: name},
	}
	if projectID != "" {
		ns.Labels = map[string]string{agent.ProjectIDLabel: projectID}
	}
	return ns
}

func createReplicaSet(namespace string, labels map[string]string) *appsv1.ReplicaSet {
	replicas := int32(1)
	return &appsv1.ReplicaSet{
		TypeMeta: metav1.TypeMeta{APIVersion: "apps/v1", Kind: "ReplicaSet"},
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-replicaset",
			Namespace: namespace,
			Labels:    labels,
		},
		Spec: appsv1.ReplicaSetSpec{
			Replicas: &replicas,
			Selector: &metav1.LabelSelector{MatchLabels: map[string]string{"app": "test-replicaset"}},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{Labels: map[string]string{"app": "test-replicaset"}},
				Spec:       corev1.PodSpec{Containers: []corev1.Container{{Name: "test", Image: "nginx"}}},
			},
		},
	}
}

func createAdmissionRequest(rs *appsv1.ReplicaSet, oldRS *appsv1.ReplicaSet) admission.Request {
	raw, _ := json.Marshal(rs)
	req := admission.Request{
		AdmissionRequest: admissionv1.AdmissionRequest{
			UID:       types.UID("test-uid-12345"),
			Kind:      metav1.GroupVersionKind{Group: "apps", Version: "v1", Kind: "ReplicaSet"},
			Namespace: rs.Namespace,
			Name:      rs.Name,
			Operation: admissionv1.Create,
			Object:    runtime.RawExtension{Raw: raw},
			UserInfo:  authenticationv1.UserInfo{Username: "test-user@example.com"},
		},
	}
	if oldRS != nil {
		oldRaw, _ := json.Marshal(oldRS)
		req.Operation = admissionv1.Update
		req.OldObject = runtime.RawExtension{Raw: oldRaw}
	}
	return req
}

func TestReplicaSetWebhook(t *testing.T) {
	scenarios := []testScenario{
		{
			name:           "CreateInAIRMNamespace",
			namespaceName:  "airm-test",
			projectID:      "project-123",
			resourceLabels: nil,
			expectedPatches: []testutils.ExpectedPatch{
				testutils.AddMetadataLabels(map[string]interface{}{
					agent.ProjectIDLabel:    "project-123",
					common.KueueNameLabel:   "airm-test",
					common.WorkloadIDLabel:  testutils.UUIDMatcher,
					common.ComponentIDLabel: testutils.UUIDMatcher,
				}),
				testutils.AddMetadataAnnotations(map[string]interface{}{
					agent.AutoDiscoveredAnnotation: "true",
					agent.SubmitterAnnotation:      "test-user@example.com",
				}),
				testutils.AddPodTemplateLabelMatching(testutils.LabelSegmentWorkloadID, testutils.UUIDMatcher),
				testutils.AddPodTemplateLabelMatching(testutils.LabelSegmentComponentID, testutils.UUIDMatcher),
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
			name:          "PreservesExistingIDs",
			namespaceName: "airm-test",
			projectID:     "project-123",
			resourceLabels: map[string]string{
				common.WorkloadIDLabel:  "custom-workload-id",
				common.ComponentIDLabel: "custom-component-id",
			},
			expectedPatches: []testutils.ExpectedPatch{
				testutils.AddMetadataLabel(testutils.LabelSegmentProjectID, "project-123"),
				testutils.AddMetadataLabel(testutils.LabelSegmentKueueName, "airm-test"),
				testutils.AddMetadataAnnotations(map[string]interface{}{agent.AutoDiscoveredAnnotation: "false"}),
				testutils.AddPodTemplateLabel(testutils.LabelSegmentWorkloadID, "custom-workload-id"),
				testutils.AddPodTemplateLabel(testutils.LabelSegmentComponentID, "custom-component-id"),
			},
			allowed: true,
		},
		{
			name:           "UpdatePreservesIDsFromOldObject",
			namespaceName:  "airm-test",
			projectID:      "project-123",
			resourceLabels: nil,
			oldRSLabels: map[string]string{
				common.WorkloadIDLabel:  "original-workload-id",
				common.ComponentIDLabel: "original-component-id",
			},
			expectedPatches: []testutils.ExpectedPatch{
				testutils.AddMetadataLabels(map[string]interface{}{
					agent.ProjectIDLabel:    "project-123",
					common.KueueNameLabel:   "airm-test",
					common.WorkloadIDLabel:  "original-workload-id",
					common.ComponentIDLabel: "original-component-id",
				}),
				testutils.AddPodTemplateLabel(testutils.LabelSegmentWorkloadID, "original-workload-id"),
				testutils.AddPodTemplateLabel(testutils.LabelSegmentComponentID, "original-component-id"),
			},
			allowed: true,
		},
		{
			name:                "SubmitterAnnotation_SetWhenEmpty",
			namespaceName:       "airm-test",
			projectID:           "project-123",
			resourceLabels:      nil,
			resourceAnnotations: nil,
			expectedPatches: []testutils.ExpectedPatch{
				testutils.AddMetadataLabels(map[string]interface{}{
					agent.ProjectIDLabel:    "project-123",
					common.KueueNameLabel:   "airm-test",
					common.WorkloadIDLabel:  testutils.UUIDMatcher,
					common.ComponentIDLabel: testutils.UUIDMatcher,
				}),
				testutils.AddMetadataAnnotations(map[string]interface{}{
					agent.AutoDiscoveredAnnotation: "true",
					agent.SubmitterAnnotation:      "test-user@example.com",
				}),
				testutils.AddPodTemplateLabelMatching(testutils.LabelSegmentWorkloadID, testutils.UUIDMatcher),
				testutils.AddPodTemplateLabelMatching(testutils.LabelSegmentComponentID, testutils.UUIDMatcher),
			},
			allowed: true,
		},
		{
			name:                "SubmitterAnnotation_PreserveWhenSet",
			namespaceName:       "airm-test",
			projectID:           "project-123",
			resourceLabels:      nil,
			resourceAnnotations: map[string]string{agent.SubmitterAnnotation: "aiwb-user@example.com"},
			expectedPatches: []testutils.ExpectedPatch{
				testutils.AddMetadataLabels(map[string]interface{}{
					agent.ProjectIDLabel:    "project-123",
					common.KueueNameLabel:   "airm-test",
					common.WorkloadIDLabel:  testutils.UUIDMatcher,
					common.ComponentIDLabel: testutils.UUIDMatcher,
				}),
				testutils.AddMetadataAnnotation(testutils.AnnotationSegmentAutoDiscovered, "true"),
				testutils.AddPodTemplateLabelMatching(testutils.LabelSegmentWorkloadID, testutils.UUIDMatcher),
				testutils.AddPodTemplateLabelMatching(testutils.LabelSegmentComponentID, testutils.UUIDMatcher),
			},
			allowed: true,
		},
	}

	for _, s := range scenarios {
		t.Run(s.name, func(t *testing.T) {
			t.Helper()
			ns := createNamespace(s.namespaceName, s.projectID)
			webhook := setupTestWebhook(ns)

			rs := createReplicaSet(s.namespaceName, s.resourceLabels)
			if s.resourceAnnotations != nil {
				rs.Annotations = s.resourceAnnotations
			}
			var oldRS *appsv1.ReplicaSet
			if s.oldRSLabels != nil {
				oldRS = createReplicaSet(s.namespaceName, s.oldRSLabels)
			}
			req := createAdmissionRequest(rs, oldRS)
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

func TestReplicaSetWebhook_NamespaceNotFound(t *testing.T) {
	webhook := setupTestWebhook()
	rs := createReplicaSet("non-existent-ns", nil)
	req := createAdmissionRequest(rs, nil)
	resp := webhook.Handle(context.Background(), req)
	require.False(t, resp.Allowed)
	require.Equal(t, int32(http.StatusInternalServerError), resp.Result.Code)
}
