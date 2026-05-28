// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package pod

import (
	"context"
	"encoding/json"
	"testing"

	agent "github.com/silogen/agent/internal/common"
	"github.com/silogen/agent/internal/testutils"
	"github.com/stretchr/testify/require"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"
	"sigs.k8s.io/controller-runtime/pkg/webhook/admission"

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
	resourceScheduler   string
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

func createPod(labels map[string]string, scheduler string) *corev1.Pod {
	return &corev1.Pod{
		TypeMeta: metav1.TypeMeta{
			APIVersion: "v1",
			Kind:       "Pod",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-pod",
			Namespace: testNamespace,
			Labels:    labels,
		},
		Spec: corev1.PodSpec{
			SchedulerName: scheduler,
			Containers: []corev1.Container{
				{Name: "test", Image: "nginx"},
			},
		},
	}
}

func createAdmissionRequest(pod *corev1.Pod, oldPod *corev1.Pod) admission.Request {
	raw, _ := json.Marshal(pod)
	var oldRaw []byte
	if oldPod != nil {
		oldRaw, _ = json.Marshal(oldPod)
	}
	return testutils.AdmissionTestCreateRequest(
		metav1.GroupVersionKind{Group: "", Version: "v1", Kind: "Pod"},
		testNamespace,
		pod.Name,
		raw,
		oldRaw,
		testUsername,
	)
}

func expectedPatchesPodAirmCreate() []testutils.ExpectedPatch {
	return []testutils.ExpectedPatch{
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
		testutils.AddPatch("/spec/schedulerName", kaiwoSchedulerName),
	}
}

func TestPodWebhook(t *testing.T) {
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
			expectedPatches: expectedPatchesPodAirmCreate(),
			allowed:         true,
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
				testutils.AddPatch("/spec/schedulerName", kaiwoSchedulerName),
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
			},
			allowed: true,
		},
		{
			name:              "AIRMNamespace_DefaultScheduleOverwritten",
			namespaceLabels:   map[string]string{agent.ProjectIDLabel: testProjectID},
			resourceScheduler: defaultSchedulerName,
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
				testutils.AddPatch("/spec/schedulerName", kaiwoSchedulerName),
			},
			allowed: true,
		},
		{
			name:              "AIRMNamespace_ExistingSchedulerNotOverwritten",
			namespaceLabels:   map[string]string{agent.ProjectIDLabel: testProjectID},
			resourceScheduler: "some-other-scheduler",
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
			},
			allowed: true,
		},
		{
			name:                "SubmitterAnnotation_SetWhenEmpty",
			namespaceLabels:     map[string]string{agent.ProjectIDLabel: testProjectID},
			resourceLabels:      nil,
			resourceAnnotations: nil,
			resourceScheduler:   "",
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
				testutils.AddPatch("/spec/schedulerName", kaiwoSchedulerName),
			},
			allowed: true,
		},
		{
			name:                "SubmitterAnnotation_PreserveWhenSet",
			namespaceLabels:     map[string]string{agent.ProjectIDLabel: testProjectID},
			resourceLabels:      nil,
			resourceAnnotations: map[string]string{agent.SubmitterAnnotation: "aiwb-user@example.com"},
			resourceScheduler:   "",
			expectedPatches: []testutils.ExpectedPatch{
				testutils.AddMetadataLabels(map[string]interface{}{
					agent.ProjectIDLabel:    testProjectID,
					common.KueueNameLabel:   testNamespace,
					common.WorkloadIDLabel:  testutils.UUIDMatcher,
					common.ComponentIDLabel: testutils.UUIDMatcher,
				}),
				testutils.AddMetadataAnnotation(testutils.AnnotationSegmentAutoDiscovered, "true"),
				testutils.AddPatch("/spec/schedulerName", kaiwoSchedulerName),
			},
			allowed: true,
		},
	}

	for _, s := range scenarios {
		t.Run(s.name, func(t *testing.T) {
			t.Helper()
			ns := createNamespace(s.namespaceLabels)
			webhook := setupWebhook(ns)

			pod := createPod(s.resourceLabels, s.resourceScheduler)
			if s.resourceAnnotations != nil {
				pod.Annotations = s.resourceAnnotations
			}
			var oldPod *corev1.Pod
			if s.oldResourceLabels != nil {
				oldPod = createPod(s.oldResourceLabels, s.resourceScheduler)
			}
			req := createAdmissionRequest(pod, oldPod)
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

func TestPodWebhook_PreservesUnknownSpecFields(t *testing.T) {
	ns := createNamespace(map[string]string{agent.ProjectIDLabel: testProjectID})
	wh := setupWebhook(ns)
	pod := createPod(nil, "")

	raw := testutils.AddUnknownKeyToJSON(t, pod)

	req := testutils.AdmissionTestCreateRequest(
		metav1.GroupVersionKind{Group: "", Version: "v1", Kind: "Pod"},
		testNamespace, pod.Name, raw, nil, testUsername,
	)
	resp := wh.Handle(context.Background(), req)
	expectedPatches := []testutils.ExpectedPatch{
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
		testutils.AddPatch("/spec/schedulerName", kaiwoSchedulerName),
	}
	testutils.AssertWebhookResponse(t, resp.Allowed, resp.Patches, expectedPatches)
}

func TestPodWebhook_NamespaceNotFound(t *testing.T) {
	// Create webhook without the target namespace
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)

	client := fake.NewClientBuilder().
		WithScheme(scheme).
		Build()

	webhook := &Webhook{
		Client:  client,
		Decoder: admission.NewDecoder(scheme),
		Logger:  zap.New(zap.UseDevMode(true)),
	}

	pod := createPod(nil, "")
	req := createAdmissionRequest(pod, nil)

	resp := webhook.Handle(context.Background(), req)

	require.False(t, resp.Allowed)
	require.Equal(t, int32(500), resp.Result.Code)
}
