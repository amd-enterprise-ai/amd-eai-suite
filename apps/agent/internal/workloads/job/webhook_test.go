// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package job

import (
	"context"
	"encoding/json"
	"net/http"
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

type testScenario struct {
	name                string
	namespaceName       string
	projectID           string
	resourceLabels      map[string]string
	resourceAnnotations map[string]string
	oldJobLabels        map[string]string
	expectedPatches     []testutils.ExpectedPatch
	allowed             bool
	resultMessage       string
}

func setupTestWebhook(objects ...runtime.Object) *Webhook {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)
	_ = batchv1.AddToScheme(scheme)

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

func createJob(namespace string, labels map[string]string) *batchv1.Job {
	return &batchv1.Job{
		TypeMeta: metav1.TypeMeta{
			APIVersion: "batch/v1",
			Kind:       "Job",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-job",
			Namespace: namespace,
			Labels:    labels,
		},
		Spec: batchv1.JobSpec{
			Template: corev1.PodTemplateSpec{
				Spec: corev1.PodSpec{
					Containers: []corev1.Container{
						{Name: "test", Image: "busybox"},
					},
					RestartPolicy: corev1.RestartPolicyNever,
				},
			},
		},
	}
}

func createAdmissionRequest(job *batchv1.Job, oldJob *batchv1.Job) admission.Request {
	raw, _ := json.Marshal(job)

	req := admission.Request{
		AdmissionRequest: admissionv1.AdmissionRequest{
			UID:       types.UID("test-uid-12345"),
			Kind:      metav1.GroupVersionKind{Group: "batch", Version: "v1", Kind: "Job"},
			Namespace: job.Namespace,
			Name:      job.Name,
			Operation: admissionv1.Create,
			Object:    runtime.RawExtension{Raw: raw},
			UserInfo: authenticationv1.UserInfo{
				Username: "test-user@example.com",
			},
		},
	}

	if oldJob != nil {
		oldRaw, _ := json.Marshal(oldJob)
		req.Operation = admissionv1.Update
		req.OldObject = runtime.RawExtension{Raw: oldRaw}
	}

	return req
}

func TestJobWebhook(t *testing.T) {
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
				testutils.AddPodTemplateLabels(map[string]interface{}{
					common.WorkloadIDLabel:  testutils.UUIDMatcher,
					common.ComponentIDLabel: testutils.UUIDMatcher,
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
				testutils.AddPodTemplateLabels(map[string]interface{}{
					common.WorkloadIDLabel:  "custom-workload-id",
					common.ComponentIDLabel: "custom-component-id",
				}),
			},
			allowed: true,
		},
		{
			name:           "UpdatePreservesIDsFromOldObject",
			namespaceName:  "airm-test",
			projectID:      "project-123",
			resourceLabels: nil,
			oldJobLabels: map[string]string{
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
				testutils.AddPodTemplateLabels(map[string]interface{}{
					common.WorkloadIDLabel:  "original-workload-id",
					common.ComponentIDLabel: "original-component-id",
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
				testutils.AddPodTemplateLabels(map[string]interface{}{
					common.WorkloadIDLabel:  testutils.UUIDMatcher,
					common.ComponentIDLabel: testutils.UUIDMatcher,
				}),
				testutils.AddMetadataLabelMatching(testutils.LabelSegmentComponentID, testutils.UUIDMatcher),
				testutils.ReplaceMetadataLabel(testutils.LabelSegmentProjectID, "project-from-ns"),
				testutils.AddMetadataLabelMatching(testutils.LabelSegmentWorkloadID, testutils.UUIDMatcher),
				testutils.AddMetadataLabel(testutils.LabelSegmentKueueName, "airm-test"),
				testutils.AddMetadataAnnotations(map[string]interface{}{
					agent.AutoDiscoveredAnnotation: "true",
					agent.SubmitterAnnotation:      "test-user@example.com",
				}),
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
				testutils.AddPodTemplateLabels(map[string]interface{}{
					common.WorkloadIDLabel:  testutils.UUIDMatcher,
					common.ComponentIDLabel: testutils.UUIDMatcher,
				}),
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
				testutils.AddPodTemplateLabels(map[string]interface{}{
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
			var webhook *Webhook
			if s.namespaceName != "" {
				ns := createNamespace(s.namespaceName, s.projectID)
				webhook = setupTestWebhook(ns)
			} else {
				webhook = setupTestWebhook()
			}

			nsName := s.namespaceName
			if nsName == "" {
				nsName = "default"
			}
			job := createJob(nsName, s.resourceLabels)
			if s.resourceAnnotations != nil {
				job.Annotations = s.resourceAnnotations
			}
			var oldJob *batchv1.Job
			if s.oldJobLabels != nil {
				oldJob = createJob(nsName, s.oldJobLabels)
				oldJob.Annotations = map[string]string{agent.AutoDiscoveredAnnotation: "true"}
			}
			req := createAdmissionRequest(job, oldJob)
			resp := webhook.Handle(context.Background(), req)

			if s.resultMessage != "" {
				require.Contains(t, resp.Result.Message, s.resultMessage)
			}
			if !s.allowed {
				require.False(t, resp.Allowed, "expected denied response")
				return
			}
			testutils.AssertWebhookResponse(t, resp.Allowed, resp.Patches, s.expectedPatches)
		})
	}
}

func TestJobWebhook_NamespaceNotFound(t *testing.T) {
	webhook := setupTestWebhook()
	job := createJob("non-existent-ns", nil)
	req := createAdmissionRequest(job, nil)
	resp := webhook.Handle(context.Background(), req)
	require.False(t, resp.Allowed)
	require.Equal(t, int32(http.StatusInternalServerError), resp.Result.Code)
}

func TestJobWebhook_AlreadyConfigured(t *testing.T) {
	ns := createNamespace("airm-test", "project-123")
	webhook := setupTestWebhook(ns)
	suspend := true
	job := &batchv1.Job{
		TypeMeta: metav1.TypeMeta{APIVersion: "batch/v1", Kind: "Job"},
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-job",
			Namespace: "airm-test",
			Labels: map[string]string{
				agent.ProjectIDLabel:    "project-123",
				common.WorkloadIDLabel:  "existing-id",
				common.ComponentIDLabel: "existing-id",
				common.KueueNameLabel:   "airm-test",
			},
			Annotations: map[string]string{
				agent.AutoDiscoveredAnnotation: "false",
				agent.SubmitterAnnotation:      "original-user",
			},
		},
		Spec: batchv1.JobSpec{
			Suspend: &suspend,
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: map[string]string{
						common.WorkloadIDLabel:  "existing-id",
						common.ComponentIDLabel: "existing-id",
					},
				},
				Spec: corev1.PodSpec{
					Containers:    []corev1.Container{{Name: "test", Image: "busybox"}},
					RestartPolicy: corev1.RestartPolicyNever,
				},
			},
		},
	}
	req := createAdmissionRequest(job, nil)
	resp := webhook.Handle(context.Background(), req)
	testutils.AssertWebhookResponse(t, resp.Allowed, resp.Patches, nil)
}
