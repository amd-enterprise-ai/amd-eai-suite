// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package statefulset

import (
	"context"
	"encoding/json"
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

const (
	testNamespace = "test-ns"
	testProjectID = "project-123"
	testUID       = "test-uid-12345"
	testUsername  = "test-user@example.com"
)

type testScenario struct {
	name                string
	namespaceLabels     map[string]string
	resourceLabels      map[string]string
	resourceAnnotations map[string]string
	oldResourceLabels   map[string]string
	expectedPatches     []testutils.ExpectedPatch
	allowed             bool
	resultMessage       string
}

func createNamespace(labels map[string]string) *corev1.Namespace {
	return &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name:   testNamespace,
			Labels: labels,
		},
	}
}

func setupWebhook(ns *corev1.Namespace) *Webhook {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)
	_ = appsv1.AddToScheme(scheme)

	client := fake.NewClientBuilder().
		WithScheme(scheme).
		WithObjects(ns).
		Build()

	return &Webhook{
		Client:  client,
		Decoder: admission.NewDecoder(scheme),
		Logger:  zap.New(zap.UseDevMode(true)),
	}
}

func createStatefulSet(labels map[string]string) *appsv1.StatefulSet {
	return &appsv1.StatefulSet{
		TypeMeta: metav1.TypeMeta{
			APIVersion: "apps/v1",
			Kind:       "StatefulSet",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-statefulset",
			Namespace: testNamespace,
			Labels:    labels,
		},
		Spec: appsv1.StatefulSetSpec{
			ServiceName: "test-svc",
			Selector:    &metav1.LabelSelector{MatchLabels: map[string]string{"app": "test"}},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{Labels: map[string]string{"app": "test"}},
				Spec:       corev1.PodSpec{Containers: []corev1.Container{{Name: "test", Image: "nginx"}}},
			},
		},
	}
}

func createAdmissionRequest(statefulSet *appsv1.StatefulSet, oldStatefulSet *appsv1.StatefulSet) admission.Request {
	raw, _ := json.Marshal(statefulSet)

	req := admission.Request{
		AdmissionRequest: admissionv1.AdmissionRequest{
			UID:       types.UID(testUID),
			Kind:      metav1.GroupVersionKind{Group: "apps", Version: "v1", Kind: "StatefulSet"},
			Namespace: testNamespace,
			Name:      statefulSet.Name,
			Operation: admissionv1.Create,
			Object:    runtime.RawExtension{Raw: raw},
			UserInfo: authenticationv1.UserInfo{
				Username: testUsername,
			},
		},
	}

	if oldStatefulSet != nil {
		oldRaw, _ := json.Marshal(oldStatefulSet)
		req.Operation = admissionv1.Update
		req.OldObject = runtime.RawExtension{Raw: oldRaw}
	}

	return req
}

func TestStatefulSetWebhook(t *testing.T) {
	scenarios := []testScenario{
		{
			name:            "NonManagedNamespace",
			namespaceLabels: nil,
			expectedPatches: nil,
			allowed:         true,
			resultMessage:   "not managed by AIRM",
		},
		{
			name:            "AIRMNamespace_NewResource",
			namespaceLabels: map[string]string{agent.ProjectIDLabel: testProjectID},
			expectedPatches: []testutils.ExpectedPatch{
				testutils.AddMetadataLabels(map[string]interface{}{
					agent.ProjectIDLabel:    testProjectID,
					common.KueueNameLabel:   testNamespace,
					common.WorkloadIDLabel:  testutils.UUIDMatcher,
					common.ComponentIDLabel: testutils.UUIDMatcher,
				}),
				testutils.AddMetadataAnnotations(map[string]interface{}{
					agent.AutoDiscoveredAnnotation: "true",
					agent.SubmitterAnnotation:      testUsername,
				}),
				testutils.AddPodTemplateLabelMatching(testutils.LabelSegmentWorkloadID, testutils.UUIDMatcher),
				testutils.AddPodTemplateLabelMatching(testutils.LabelSegmentComponentID, testutils.UUIDMatcher),
			},
			allowed: true,
		},
		{
			name:            "AIRMNamespace_PreservesExistingIDs",
			namespaceLabels: map[string]string{agent.ProjectIDLabel: testProjectID},
			resourceLabels: map[string]string{
				common.WorkloadIDLabel:  "custom-workload-id",
				common.ComponentIDLabel: "custom-component-id",
			},
			expectedPatches: []testutils.ExpectedPatch{
				testutils.AddMetadataLabel(testutils.LabelSegmentProjectID, testProjectID),
				testutils.AddMetadataLabel(testutils.LabelSegmentKueueName, testNamespace),
				testutils.AddMetadataAnnotations(map[string]interface{}{agent.AutoDiscoveredAnnotation: "false"}),
				testutils.AddPodTemplateLabel(testutils.LabelSegmentWorkloadID, "custom-workload-id"),
				testutils.AddPodTemplateLabel(testutils.LabelSegmentComponentID, "custom-component-id"),
			},
			allowed: true,
		},
		{
			name:            "AIRMNamespace_UpdateRecovery",
			namespaceLabels: map[string]string{agent.ProjectIDLabel: testProjectID},
			oldResourceLabels: map[string]string{
				common.WorkloadIDLabel:  "original-workload-id",
				common.ComponentIDLabel: "original-component-id",
			},
			expectedPatches: []testutils.ExpectedPatch{
				testutils.AddMetadataLabels(map[string]interface{}{
					agent.ProjectIDLabel:    testProjectID,
					common.KueueNameLabel:   testNamespace,
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
			namespaceLabels:     map[string]string{agent.ProjectIDLabel: testProjectID},
			resourceLabels:      nil,
			resourceAnnotations: nil,
			expectedPatches: []testutils.ExpectedPatch{
				testutils.AddMetadataLabels(map[string]interface{}{
					agent.ProjectIDLabel:    testProjectID,
					common.KueueNameLabel:   testNamespace,
					common.WorkloadIDLabel:  testutils.UUIDMatcher,
					common.ComponentIDLabel: testutils.UUIDMatcher,
				}),
				testutils.AddMetadataAnnotations(map[string]interface{}{
					agent.AutoDiscoveredAnnotation: "true",
					agent.SubmitterAnnotation:      testUsername,
				}),
				testutils.AddPodTemplateLabelMatching(testutils.LabelSegmentWorkloadID, testutils.UUIDMatcher),
				testutils.AddPodTemplateLabelMatching(testutils.LabelSegmentComponentID, testutils.UUIDMatcher),
			},
			allowed: true,
		},
		{
			name:                "SubmitterAnnotation_PreserveWhenSet",
			namespaceLabels:     map[string]string{agent.ProjectIDLabel: testProjectID},
			resourceLabels:      nil,
			resourceAnnotations: map[string]string{agent.SubmitterAnnotation: "aiwb-user@example.com"},
			expectedPatches: []testutils.ExpectedPatch{
				testutils.AddMetadataLabels(map[string]interface{}{
					agent.ProjectIDLabel:    testProjectID,
					common.KueueNameLabel:   testNamespace,
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
			ns := createNamespace(s.namespaceLabels)
			webhook := setupWebhook(ns)

			sts := createStatefulSet(s.resourceLabels)
			if s.resourceAnnotations != nil {
				sts.Annotations = s.resourceAnnotations
			}
			var oldSTS *appsv1.StatefulSet
			if s.oldResourceLabels != nil {
				oldSTS = createStatefulSet(s.oldResourceLabels)
			}
			req := createAdmissionRequest(sts, oldSTS)
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

func TestStatefulSetWebhook_NamespaceNotFound(t *testing.T) {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)
	_ = appsv1.AddToScheme(scheme)

	client := fake.NewClientBuilder().
		WithScheme(scheme).
		Build()

	webhook := &Webhook{
		Client:  client,
		Decoder: admission.NewDecoder(scheme),
		Logger:  zap.New(zap.UseDevMode(true)),
	}

	statefulSet := createStatefulSet(nil)
	req := createAdmissionRequest(statefulSet, nil)

	resp := webhook.Handle(context.Background(), req)

	require.False(t, resp.Allowed)
	require.Equal(t, int32(500), resp.Result.Code)
}
