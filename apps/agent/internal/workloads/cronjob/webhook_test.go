// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package cronjob

import (
	"context"
	"encoding/json"
	"testing"

	agent "github.com/silogen/agent/internal/common"
	"github.com/silogen/agent/internal/testutils"
	"github.com/stretchr/testify/require"
	admissionv1 "k8s.io/api/admission/v1"
	authenticationv1 "k8s.io/api/authentication/v1"
	batchv1 "k8s.io/api/batch/v1"
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
	testNamespace            = "test-ns"
	testProjectID            = "project-123"
	testUID                  = "test-uid-12345"
	testUsername             = "test-user@example.com"
	jobTemplateLabelsPath    = "/spec/jobTemplate/metadata/labels"
	jobTemplatePodLabelsPath = "/spec/jobTemplate/spec/template/metadata/labels"
)

func addJobTemplateLabels(value map[string]interface{}) testutils.ExpectedPatch {
	return testutils.ExpectedPatch{Operation: "add", Path: jobTemplateLabelsPath, Value: value}
}

func addJobTemplatePodLabels(value map[string]interface{}) testutils.ExpectedPatch {
	return testutils.ExpectedPatch{Operation: "add", Path: jobTemplatePodLabelsPath, Value: value}
}

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
	_ = batchv1.AddToScheme(scheme)

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

func createCronJob(labels map[string]string) *batchv1.CronJob {
	return &batchv1.CronJob{
		TypeMeta: metav1.TypeMeta{
			APIVersion: "batch/v1",
			Kind:       "CronJob",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-cronjob",
			Namespace: testNamespace,
			Labels:    labels,
		},
		Spec: batchv1.CronJobSpec{
			Schedule: "*/5 * * * *",
			JobTemplate: batchv1.JobTemplateSpec{
				Spec: batchv1.JobSpec{
					Template: corev1.PodTemplateSpec{
						Spec: corev1.PodSpec{
							Containers:    []corev1.Container{{Name: "test", Image: "busybox"}},
							RestartPolicy: corev1.RestartPolicyNever,
						},
					},
				},
			},
		},
	}
}

func createAdmissionRequest(cronJob *batchv1.CronJob, oldCronJob *batchv1.CronJob) admission.Request {
	raw, _ := json.Marshal(cronJob)

	req := admission.Request{
		AdmissionRequest: admissionv1.AdmissionRequest{
			UID:       types.UID(testUID),
			Kind:      metav1.GroupVersionKind{Group: "batch", Version: "v1", Kind: "CronJob"},
			Namespace: testNamespace,
			Name:      cronJob.Name,
			Operation: admissionv1.Create,
			Object:    runtime.RawExtension{Raw: raw},
			UserInfo: authenticationv1.UserInfo{
				Username: testUsername,
			},
		},
	}

	if oldCronJob != nil {
		oldRaw, _ := json.Marshal(oldCronJob)
		req.Operation = admissionv1.Update
		req.OldObject = runtime.RawExtension{Raw: oldRaw}
	}

	return req
}

func TestCronJobWebhook(t *testing.T) {
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
				addJobTemplateLabels(map[string]interface{}{
					common.KueueNameLabel:   testNamespace,
					common.WorkloadIDLabel:  testutils.UUIDMatcher,
					common.ComponentIDLabel: testutils.UUIDMatcher,
				}),
				addJobTemplatePodLabels(map[string]interface{}{
					common.WorkloadIDLabel:  testutils.UUIDMatcher,
					common.ComponentIDLabel: testutils.UUIDMatcher,
				}),
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
				addJobTemplateLabels(map[string]interface{}{
					common.KueueNameLabel:   testNamespace,
					common.WorkloadIDLabel:  "custom-workload-id",
					common.ComponentIDLabel: "custom-component-id",
				}),
				addJobTemplatePodLabels(map[string]interface{}{
					common.WorkloadIDLabel:  "custom-workload-id",
					common.ComponentIDLabel: "custom-component-id",
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
				addJobTemplateLabels(map[string]interface{}{
					common.KueueNameLabel:   testNamespace,
					common.WorkloadIDLabel:  "original-workload-id",
					common.ComponentIDLabel: "original-component-id",
				}),
				addJobTemplatePodLabels(map[string]interface{}{
					common.WorkloadIDLabel:  "original-workload-id",
					common.ComponentIDLabel: "original-component-id",
				}),
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
				addJobTemplateLabels(map[string]interface{}{
					common.WorkloadIDLabel:  testutils.UUIDMatcher,
					common.ComponentIDLabel: testutils.UUIDMatcher,
					common.KueueNameLabel:   testNamespace,
				}),
				addJobTemplatePodLabels(map[string]interface{}{
					common.WorkloadIDLabel:  testutils.UUIDMatcher,
					common.ComponentIDLabel: testutils.UUIDMatcher,
				}),
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
				addJobTemplateLabels(map[string]interface{}{
					common.WorkloadIDLabel:  testutils.UUIDMatcher,
					common.ComponentIDLabel: testutils.UUIDMatcher,
					common.KueueNameLabel:   testNamespace,
				}),
				addJobTemplatePodLabels(map[string]interface{}{
					common.WorkloadIDLabel:  testutils.UUIDMatcher,
					common.ComponentIDLabel: testutils.UUIDMatcher,
				}),
			},
			allowed: true,
		},
	}

	for _, s := range scenarios {
		t.Run(s.name, func(t *testing.T) {
			t.Helper()
			ns := createNamespace(s.namespaceLabels)
			webhook := setupWebhook(ns)

			cj := createCronJob(s.resourceLabels)
			if s.resourceAnnotations != nil {
				cj.Annotations = s.resourceAnnotations
			}
			var oldCJ *batchv1.CronJob
			if s.oldResourceLabels != nil {
				oldCJ = createCronJob(s.oldResourceLabels)
			}
			req := createAdmissionRequest(cj, oldCJ)
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

func TestCronJobWebhook_NamespaceNotFound(t *testing.T) {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)
	_ = batchv1.AddToScheme(scheme)

	client := fake.NewClientBuilder().
		WithScheme(scheme).
		Build()

	webhook := &Webhook{
		Client:  client,
		Decoder: admission.NewDecoder(scheme),
		Logger:  zap.New(zap.UseDevMode(true)),
	}

	cronJob := createCronJob(nil)
	req := createAdmissionRequest(cronJob, nil)

	resp := webhook.Handle(context.Background(), req)

	require.False(t, resp.Allowed)
	require.Equal(t, int32(500), resp.Result.Code)
}
