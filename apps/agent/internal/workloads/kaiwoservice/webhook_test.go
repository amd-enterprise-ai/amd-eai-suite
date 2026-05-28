// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package kaiwoservice

import (
	"context"
	"encoding/json"
	"testing"

	agent "github.com/silogen/agent/internal/common"
	"github.com/silogen/agent/internal/testutils"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"
	"sigs.k8s.io/controller-runtime/pkg/webhook/admission"

	kaiwov1alpha1 "github.com/silogen/kaiwo/apis/kaiwo/v1alpha1"

	"github.com/silogen/agent/internal/workloads/common"
)

const (
	testNamespace = "test-ns"
	testProjectID = "project-123"
	testUsername  = "test-user@example.com"
)

type testScenario struct {
	name                string
	namespaceLabels     map[string]string
	resourceLabels      map[string]string
	resourceAnnotations map[string]string
	clusterQueue        string
	oldResourceLabels   map[string]string
	oldClusterQueue     string
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
	_ = kaiwov1alpha1.AddToScheme(scheme)

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

func createKaiwoService(labels map[string]string, clusterQueue string) *kaiwov1alpha1.KaiwoService {
	return &kaiwov1alpha1.KaiwoService{
		TypeMeta: metav1.TypeMeta{
			APIVersion: "kaiwo.silogen.ai/v1alpha1",
			Kind:       "KaiwoService",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-kaiwoservice",
			Namespace: testNamespace,
			Labels:    labels,
		},
		Spec: kaiwov1alpha1.KaiwoServiceSpec{
			CommonMetaSpec: kaiwov1alpha1.CommonMetaSpec{
				User:         testUsername,
				Image:        "nginx:latest",
				ClusterQueue: clusterQueue,
			},
		},
	}
}

func createAdmissionRequest(kaiwoService *kaiwov1alpha1.KaiwoService, oldKaiwoService *kaiwov1alpha1.KaiwoService) admission.Request {
	raw, _ := json.Marshal(kaiwoService)
	var oldRaw []byte
	if oldKaiwoService != nil {
		oldRaw, _ = json.Marshal(oldKaiwoService)
	}
	return testutils.AdmissionTestCreateRequest(
		metav1.GroupVersionKind{Group: "kaiwo.silogen.ai", Version: "v1alpha1", Kind: "KaiwoService"},
		testNamespace,
		kaiwoService.Name,
		raw,
		oldRaw,
		testUsername,
	)
}

func TestKaiwoServiceWebhook(t *testing.T) {
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
					common.WorkloadIDLabel:  testutils.UUIDMatcher,
					common.ComponentIDLabel: testutils.UUIDMatcher,
				}),
				testutils.AddMetadataAnnotations(map[string]interface{}{
					agent.AutoDiscoveredAnnotation: "true",
					agent.SubmitterAnnotation:      testUsername,
				}),
				testutils.AddPatch("/spec/clusterQueue", testNamespace),
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
				testutils.AddMetadataAnnotations(map[string]interface{}{agent.AutoDiscoveredAnnotation: "false"}),
				testutils.AddPatch("/spec/clusterQueue", testNamespace),
			},
			allowed: true,
		},
		{
			name:            "AIRMNamespace_PreservesExistingClusterQueue",
			namespaceLabels: map[string]string{agent.ProjectIDLabel: testProjectID},
			clusterQueue:    "custom-queue",
			expectedPatches: []testutils.ExpectedPatch{
				testutils.AddMetadataLabels(map[string]interface{}{
					agent.ProjectIDLabel:    testProjectID,
					common.WorkloadIDLabel:  testutils.UUIDMatcher,
					common.ComponentIDLabel: testutils.UUIDMatcher,
				}),
				testutils.AddMetadataAnnotations(map[string]interface{}{
					agent.AutoDiscoveredAnnotation: "true",
					agent.SubmitterAnnotation:      testUsername,
				}),
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
					common.WorkloadIDLabel:  "original-workload-id",
					common.ComponentIDLabel: "original-component-id",
				}),
				testutils.AddPatch("/spec/clusterQueue", testNamespace),
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
					common.WorkloadIDLabel:  testutils.UUIDMatcher,
					common.ComponentIDLabel: testutils.UUIDMatcher,
				}),
				testutils.AddMetadataAnnotations(map[string]interface{}{
					agent.AutoDiscoveredAnnotation: "true",
					agent.SubmitterAnnotation:      testUsername,
				}),
				testutils.AddPatch("/spec/clusterQueue", testNamespace),
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
					common.WorkloadIDLabel:  testutils.UUIDMatcher,
					common.ComponentIDLabel: testutils.UUIDMatcher,
				}),
				testutils.AddMetadataAnnotation(testutils.AnnotationSegmentAutoDiscovered, "true"),
				testutils.AddPatch("/spec/clusterQueue", testNamespace),
			},
			allowed: true,
		},
	}

	for _, scenario := range scenarios {
		t.Run(scenario.name, func(t *testing.T) {
			ns := createNamespace(scenario.namespaceLabels)
			webhook := setupWebhook(ns)

			kaiwoService := createKaiwoService(scenario.resourceLabels, scenario.clusterQueue)
			if scenario.resourceAnnotations != nil {
				kaiwoService.Annotations = scenario.resourceAnnotations
			}

			var oldKaiwoService *kaiwov1alpha1.KaiwoService
			if scenario.oldResourceLabels != nil {
				oldKaiwoService = createKaiwoService(scenario.oldResourceLabels, scenario.oldClusterQueue)
			}

			req := createAdmissionRequest(kaiwoService, oldKaiwoService)
			resp := webhook.Handle(context.Background(), req)

			if scenario.resultMessage != "" {
				require.Contains(t, resp.Result.Message, scenario.resultMessage)
			}
			if !scenario.allowed {
				require.False(t, resp.Allowed)
				return
			}
			testutils.AssertWebhookResponse(t, resp.Allowed, resp.Patches, scenario.expectedPatches)
		})
	}
}

func TestKaiwoServiceWebhook_PreservesUnknownSpecFields(t *testing.T) {
	ns := createNamespace(map[string]string{agent.ProjectIDLabel: testProjectID})
	wh := setupWebhook(ns)
	ks := createKaiwoService(nil, "")

	raw := testutils.AddUnknownKeyToJSON(t, ks)

	req := testutils.AdmissionTestCreateRequest(
		metav1.GroupVersionKind{Group: "kaiwo.silogen.ai", Version: "v1alpha1", Kind: "KaiwoService"},
		testNamespace, ks.Name, raw, nil, testUsername,
	)
	resp := wh.Handle(context.Background(), req)
	expectedPatches := []testutils.ExpectedPatch{
		testutils.AddMetadataLabels(map[string]interface{}{
			agent.ProjectIDLabel:    testProjectID,
			common.WorkloadIDLabel:  testutils.UUIDMatcher,
			common.ComponentIDLabel: testutils.UUIDMatcher,
		}),
		testutils.AddMetadataAnnotations(map[string]interface{}{
			agent.AutoDiscoveredAnnotation: "true",
			agent.SubmitterAnnotation:      testUsername,
		}),
		testutils.AddPatch("/spec/clusterQueue", testNamespace),
	}
	testutils.AssertWebhookResponse(t, resp.Allowed, resp.Patches, expectedPatches)
}

func TestKaiwoServiceWebhook_NamespaceNotFound(t *testing.T) {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)
	_ = kaiwov1alpha1.AddToScheme(scheme)

	client := fake.NewClientBuilder().
		WithScheme(scheme).
		Build()

	webhook := &Webhook{
		Client:  client,
		Decoder: admission.NewDecoder(scheme),
		Logger:  zap.New(zap.UseDevMode(true)),
	}

	kaiwoService := createKaiwoService(nil, "")
	req := createAdmissionRequest(kaiwoService, nil)

	resp := webhook.Handle(context.Background(), req)

	assert.False(t, resp.Allowed)
	assert.Equal(t, int32(500), resp.Result.Code)
}
