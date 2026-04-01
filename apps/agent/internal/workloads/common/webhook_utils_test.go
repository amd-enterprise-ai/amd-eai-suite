// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package common

import (
	"context"
	"encoding/json"
	"testing"

	agent "github.com/silogen/agent/internal/common"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	admissionv1 "k8s.io/api/admission/v1"
	authenticationv1 "k8s.io/api/authentication/v1"
	batchv1 "k8s.io/api/batch/v1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
	"sigs.k8s.io/controller-runtime/pkg/webhook/admission"
)

func TestGetProjectIdFromNamespace_AIRMManaged(t *testing.T) {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)

	ns := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name: "test-ns",
			Labels: map[string]string{
				agent.ProjectIDLabel: "project-123",
			},
		},
	}

	client := fake.NewClientBuilder().WithScheme(scheme).WithObjects(ns).Build()

	ctx := context.Background()
	nsCtx, err := agent.GetProjectIdFromNamespace(ctx, client, "test-ns")

	require.NoError(t, err)
	require.NotNil(t, nsCtx)
	assert.Equal(t, "project-123", nsCtx.ProjectID)
}

func TestGetProjectIdFromNamespace_NotAIRMManaged(t *testing.T) {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)

	ns := &corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name: "test-ns",
			// No project-id label
		},
	}

	client := fake.NewClientBuilder().WithScheme(scheme).WithObjects(ns).Build()

	ctx := context.Background()
	nsCtx, err := agent.GetProjectIdFromNamespace(ctx, client, "test-ns")

	require.NoError(t, err)
	assert.Nil(t, nsCtx)
}

func TestGetProjectIdFromNamespace_NotFound(t *testing.T) {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)

	client := fake.NewClientBuilder().WithScheme(scheme).Build()

	ctx := context.Background()
	nsCtx, err := agent.GetProjectIdFromNamespace(ctx, client, "non-existent")

	require.Error(t, err)
	assert.Nil(t, nsCtx)
}

func createTestAdmissionRequest(name, kind string) admission.Request {
	return admission.Request{
		AdmissionRequest: admissionv1.AdmissionRequest{
			UID:       types.UID("test-uid-123"),
			Namespace: "test-ns",
			Name:      name,
			Kind:      metav1.GroupVersionKind{Kind: kind},
			Operation: admissionv1.Create,
			UserInfo:  authenticationv1.UserInfo{Username: "test-user"},
		},
	}
}

func TestApplyWorkloadTracking_NewResource(t *testing.T) {
	job := &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-job",
			Namespace: "test-ns",
		},
	}

	req := createTestAdmissionRequest("test-job", "Job")
	nsCtx := &agent.NamespaceContext{ProjectID: "project-456"}

	ApplyWorkloadTracking(job, req, nsCtx)

	labels := job.GetLabels()
	assert.Equal(t, "project-456", labels[agent.ProjectIDLabel])

	assert.NotEmpty(t, labels[WorkloadIDLabel])
	assert.NotEmpty(t, labels[ComponentIDLabel])
	assert.NotEqual(t, "test-uid-123", labels[WorkloadIDLabel], "should generate UUID, not use req.UID")
	assert.NotEqual(t, "test-uid-123", labels[ComponentIDLabel], "should generate UUID, not use req.UID")

	// Check annotations
	annotations := job.GetAnnotations()
	assert.Equal(t, "true", annotations[agent.AutoDiscoveredAnnotation])
	assert.Equal(t, "test-user", annotations[agent.SubmitterAnnotation])
}

func TestApplyWorkloadTracking_PreExistingIDs(t *testing.T) {
	job := &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-job",
			Namespace: "test-ns",
			Labels: map[string]string{
				WorkloadIDLabel:  "existing-workload-id",
				ComponentIDLabel: "existing-component-id",
			},
		},
	}

	req := createTestAdmissionRequest("test-job", "Job")
	nsCtx := &agent.NamespaceContext{ProjectID: "project-456"}

	ApplyWorkloadTracking(job, req, nsCtx)

	labels := job.GetLabels()
	assert.Equal(t, "existing-workload-id", labels[WorkloadIDLabel])
	assert.Equal(t, "existing-component-id", labels[ComponentIDLabel])
	assert.Equal(t, "project-456", labels[agent.ProjectIDLabel])

	// Should be explicitly marked as NOT auto-discovered
	annotations := job.GetAnnotations()
	assert.Equal(t, "false", annotations[agent.AutoDiscoveredAnnotation])
}

func TestApplyWorkloadTracking_UpdatePreservesIDsFromOldObject(t *testing.T) {
	// New object without IDs
	job := &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-job",
			Namespace: "test-ns",
		},
	}

	// Old object with IDs
	oldJob := &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-job",
			Namespace: "test-ns",
			Labels: map[string]string{
				WorkloadIDLabel:  "old-workload-id",
				ComponentIDLabel: "old-component-id",
			},
		},
	}
	oldRaw, _ := json.Marshal(oldJob)

	req := createTestAdmissionRequest("test-job", "Job")
	req.Operation = admissionv1.Update
	req.OldObject = runtime.RawExtension{Raw: oldRaw}
	nsCtx := &agent.NamespaceContext{ProjectID: "project-456"}

	ApplyWorkloadTracking(job, req, nsCtx)

	labels := job.GetLabels()
	assert.Equal(t, "old-workload-id", labels[WorkloadIDLabel])
	assert.Equal(t, "old-component-id", labels[ComponentIDLabel])

	// Should NOT be auto-discovered (annotation not set or false)
	annotations := job.GetAnnotations()
	assert.NotEqual(t, agent.AutoDiscoveredValue, annotations[agent.AutoDiscoveredAnnotation])
}

func TestEnsureKueueLabel(t *testing.T) {
	job := &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-job",
			Namespace: "test-ns",
		},
	}

	EnsureKueueLabel(job, "my-namespace")

	labels := job.GetLabels()
	assert.Equal(t, "my-namespace", labels[KueueNameLabel])
}

func TestEnsureKueueLabel_ExistingLabels(t *testing.T) {
	job := &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-job",
			Namespace: "test-ns",
			Labels: map[string]string{
				"existing": "label",
			},
		},
	}

	EnsureKueueLabel(job, "my-namespace")

	labels := job.GetLabels()
	assert.Equal(t, "my-namespace", labels[KueueNameLabel])
	assert.Equal(t, "label", labels["existing"])
}

func TestPropagateTrackingLabelsToTemplate(t *testing.T) {
	job := &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-job",
			Namespace: "test-ns",
			Labels: map[string]string{
				WorkloadIDLabel:  "workload-123",
				ComponentIDLabel: "component-456",
				"other-label":    "value",
			},
		},
	}

	templateLabels := map[string]string{
		"app": "myapp",
	}

	result := PropagateTrackingLabelsToTemplate(job, templateLabels)

	assert.Equal(t, "workload-123", result[WorkloadIDLabel])
	assert.Equal(t, "component-456", result[ComponentIDLabel])
	assert.Equal(t, "myapp", result["app"])
	// Should NOT copy other labels
	_, hasOther := result["other-label"]
	assert.False(t, hasOther)
}

func TestPropagateTrackingLabelsToTemplate_NilInput(t *testing.T) {
	job := &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-job",
			Namespace: "test-ns",
			Labels: map[string]string{
				WorkloadIDLabel:  "workload-123",
				ComponentIDLabel: "component-456",
			},
		},
	}

	result := PropagateTrackingLabelsToTemplate(job, nil)

	assert.Equal(t, "workload-123", result[WorkloadIDLabel])
	assert.Equal(t, "component-456", result[ComponentIDLabel])
}

func TestGetLabelsFromRaw(t *testing.T) {
	job := &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-job",
			Namespace: "test-ns",
			Labels: map[string]string{
				"key1": "value1",
				"key2": "value2",
			},
		},
	}
	raw, _ := json.Marshal(job)

	labels := agent.GetLabelsFromRaw(raw)

	assert.Equal(t, "value1", labels["key1"])
	assert.Equal(t, "value2", labels["key2"])
}

func TestGetLabelsFromRaw_InvalidJSON(t *testing.T) {
	labels := agent.GetLabelsFromRaw([]byte("invalid json"))
	assert.Nil(t, labels)
}

func TestGetLabelsFromRaw_EmptyLabels(t *testing.T) {
	job := &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-job",
			Namespace: "test-ns",
		},
	}
	raw, _ := json.Marshal(job)

	labels := agent.GetLabelsFromRaw(raw)
	assert.Empty(t, labels)
}

func TestApplyWorkloadTracking_PodWithOwner(t *testing.T) {
	// Pod without tracking IDs should be auto-discovered regardless of owner
	pod := &corev1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-pod",
			Namespace: "test-ns",
			OwnerReferences: []metav1.OwnerReference{
				{
					APIVersion: "v1",
					Kind:       "ReplicaSet",
					Name:       "parent-replicaset",
					UID:        "replicaset-uid",
				},
			},
		},
	}

	req := createTestAdmissionRequest("test-pod", "Pod")
	nsCtx := &agent.NamespaceContext{ProjectID: "project-456"}

	ApplyWorkloadTracking(pod, req, nsCtx)

	// Pod without tracking IDs should be auto-discovered
	annotations := pod.GetAnnotations()
	assert.Equal(t, agent.AutoDiscoveredValue, annotations[agent.AutoDiscoveredAnnotation])
	assert.Equal(t, "test-user", annotations[agent.SubmitterAnnotation])
}

func TestApplyWorkloadTracking_NonAutoDiscoverableKind(t *testing.T) {
	// In practice, webhooks are only registered for workload kinds, so this function
	// won't be called for ConfigMap. This test validates the function still works correctly.
	cm := &corev1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-configmap",
			Namespace: "test-ns",
		},
	}

	req := createTestAdmissionRequest("test-configmap", "ConfigMap")
	nsCtx := &agent.NamespaceContext{ProjectID: "project-456"}

	ApplyWorkloadTracking(cm, req, nsCtx)

	// ConfigMap would be marked as auto-discovered since no tracking IDs exist
	annotations := cm.GetAnnotations()
	assert.Equal(t, agent.AutoDiscoveredValue, annotations[agent.AutoDiscoveredAnnotation])
	assert.Equal(t, "test-user", annotations[agent.SubmitterAnnotation])

	// Should still get tracking labels
	labels := cm.GetLabels()
	assert.NotEmpty(t, labels[WorkloadIDLabel])
	assert.NotEmpty(t, labels[ComponentIDLabel])
	assert.Equal(t, "project-456", labels[agent.ProjectIDLabel])
}

func TestApplyWorkloadTracking_InheritedLabelsAndAnnotations(t *testing.T) {
	// Simulates a child resource (e.g., Pod) created by a parent (e.g., Deployment)
	// where both tracking labels AND auto-discovered annotation are inherited from the parent.
	// The child should be marked as NOT auto-discovered since it has tracking IDs.
	pod := &corev1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-deployment-pod",
			Namespace: "test-ns",
			Labels: map[string]string{
				WorkloadIDLabel:  "parent-workload-id",
				ComponentIDLabel: "parent-component-id",
			},
			Annotations: map[string]string{
				agent.AutoDiscoveredAnnotation: agent.AutoDiscoveredValue, // Inherited "true" from parent
				agent.SubmitterAnnotation:      "parent-user",             // Inherited from parent
			},
		},
	}

	req := createTestAdmissionRequest("test-deployment-pod", "Pod")
	nsCtx := &agent.NamespaceContext{ProjectID: "project-456"}

	ApplyWorkloadTracking(pod, req, nsCtx)

	labels := pod.GetLabels()
	// Should preserve the inherited tracking IDs
	assert.Equal(t, "parent-workload-id", labels[WorkloadIDLabel])
	assert.Equal(t, "parent-component-id", labels[ComponentIDLabel])

	// Should be explicitly marked as NOT auto-discovered since it has tracking IDs
	annotations := pod.GetAnnotations()
	assert.Equal(t, "false", annotations[agent.AutoDiscoveredAnnotation],
		"Child resource with inherited tracking IDs should NOT be auto-discovered")
}

func TestApplyWorkloadTracking_FreshResourceAlreadyMarkedAutoDiscovered(t *testing.T) {
	// Fresh resource (no tracking IDs) that already has auto-discovered=true.
	// The webhook should preserve this and not overwrite the submitter.
	pod := &corev1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-pod",
			Namespace: "test-ns",
			Annotations: map[string]string{
				agent.AutoDiscoveredAnnotation: agent.AutoDiscoveredValue,
				agent.SubmitterAnnotation:      "original-user",
			},
		},
	}

	req := createTestAdmissionRequest("test-pod", "Pod")
	nsCtx := &agent.NamespaceContext{ProjectID: "project-456"}

	ApplyWorkloadTracking(pod, req, nsCtx)

	// Should generate new tracking IDs since none existed
	labels := pod.GetLabels()
	assert.NotEmpty(t, labels[WorkloadIDLabel])
	assert.NotEmpty(t, labels[ComponentIDLabel])

	// Should preserve auto-discovered=true and existing submitter
	annotations := pod.GetAnnotations()
	assert.Equal(t, agent.AutoDiscoveredValue, annotations[agent.AutoDiscoveredAnnotation],
		"Should preserve auto-discovered when already set")
	assert.Equal(t, "original-user", annotations[agent.SubmitterAnnotation],
		"Should preserve existing submitter when annotation was already set")
}

func TestApplyWorkloadTracking_ChildDeploymentFromKaiwoService(t *testing.T) {
	// Real-world scenario: KaiwoService creates a Deployment, Kaiwo controller
	// copies all labels and annotations to the child Deployment.
	// When the Deployment goes through the webhook, it should be marked as NOT auto-discovered
	// because it has tracking IDs (inherited from the parent).
	deployment := &corev1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "kaiwoservice-deployment",
			Namespace: "test-ns",
			Labels: map[string]string{
				WorkloadIDLabel:      "kaiwo-workload-123",
				ComponentIDLabel:     "kaiwo-component-456",
				agent.ProjectIDLabel: "project-789",
			},
			Annotations: map[string]string{
				agent.AutoDiscoveredAnnotation: "true",
				agent.SubmitterAnnotation:      "kaiwo-user@example.com",
			},
			OwnerReferences: []metav1.OwnerReference{
				{
					APIVersion: "kaiwo.silogen.ai/v1alpha1",
					Kind:       "KaiwoService",
					Name:       "parent-kaiwoservice",
					UID:        "kaiwoservice-uid",
				},
			},
		},
	}

	req := createTestAdmissionRequest("kaiwoservice-deployment", "Deployment")
	nsCtx := &agent.NamespaceContext{ProjectID: "project-789"}

	ApplyWorkloadTracking(deployment, req, nsCtx)

	annotations := deployment.GetAnnotations()
	assert.Equal(t, "false", annotations[agent.AutoDiscoveredAnnotation],
		"Deployment created by KaiwoService should NOT be auto-discovered")

	// Tracking labels should be preserved
	labels := deployment.GetLabels()
	assert.Equal(t, "kaiwo-workload-123", labels[WorkloadIDLabel])
	assert.Equal(t, "kaiwo-component-456", labels[ComponentIDLabel])
}

// TestApplyWorkloadTracking_SubmitterPreservation_Job tests that the submitter annotation
// is preserved when already set (e.g., by AIWB). Webhook integration tests cover all resource types.
func TestApplyWorkloadTracking_SubmitterPreservation_Job(t *testing.T) {
	job := &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "aiwb-job",
			Namespace: "test-ns",
			Annotations: map[string]string{
				agent.SubmitterAnnotation: "aiwb-user@example.com",
			},
		},
	}

	req := createTestAdmissionRequest("aiwb-job", "Job")
	nsCtx := &agent.NamespaceContext{ProjectID: "project-456"}

	ApplyWorkloadTracking(job, req, nsCtx)

	annotations := job.GetAnnotations()
	assert.Equal(t, agent.AutoDiscoveredValue, annotations[agent.AutoDiscoveredAnnotation],
		"Job should be marked as auto-discovered since no tracking IDs exist")
	assert.Equal(t, "aiwb-user@example.com", annotations[agent.SubmitterAnnotation],
		"Should preserve AIWB-set submitter annotation, not overwrite with webhook user")
}

// TestApplyWorkloadTracking_SubmitterDefault_NoExistingAnnotation tests that
// the webhook sets the submitter to the request user when no annotation exists
func TestApplyWorkloadTracking_SubmitterDefault_NoExistingAnnotation(t *testing.T) {
	job := &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "kubectl-job",
			Namespace: "test-ns",
		},
	}

	req := createTestAdmissionRequest("kubectl-job", "Job")
	nsCtx := &agent.NamespaceContext{ProjectID: "project-456"}

	ApplyWorkloadTracking(job, req, nsCtx)

	annotations := job.GetAnnotations()
	assert.Equal(t, agent.AutoDiscoveredValue, annotations[agent.AutoDiscoveredAnnotation])
	assert.Equal(t, "test-user", annotations[agent.SubmitterAnnotation],
		"Should set submitter to webhook request user when no annotation exists")
}
