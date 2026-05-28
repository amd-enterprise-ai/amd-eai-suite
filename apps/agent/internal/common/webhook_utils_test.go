// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package common

import (
	"encoding/json"
	"testing"

	"github.com/go-logr/logr"
	"github.com/silogen/agent/internal/testutils"
	"github.com/stretchr/testify/require"
	admissionv1 "k8s.io/api/admission/v1"
	authenticationv1 "k8s.io/api/authentication/v1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	"sigs.k8s.io/controller-runtime/pkg/webhook/admission"
)

func TestCreatePatchResponse_PreservesUnknownSpecFields(t *testing.T) {
	raw := []byte(`{
		"apiVersion":"v1",
		"kind":"Pod",
		"metadata":{"name":"p","namespace":"ns"},
		"spec":{
			"clusterOnlyField": true,
			"containers":[{"name":"c","image":"img","unknownSidecar":42, "resources": {}}]
		},
		"status": {}
	}`)
	var pod corev1.Pod
	require.NoError(t, json.Unmarshal(raw, &pod))
	pod.Labels = map[string]string{"project-id": "proj"}

	req := admission.Request{
		AdmissionRequest: admissionv1.AdmissionRequest{
			UID:       types.UID("test-uid"),
			Namespace: "ns",
			Name:      "p",
			Kind:      metav1.GroupVersionKind{Group: "", Version: "v1", Kind: "Pod"},
			Operation: admissionv1.Create,
			UserInfo:  authenticationv1.UserInfo{Username: "test-user"},
			Object:    runtime.RawExtension{Raw: raw},
		},
	}

	resp := CreatePatchResponse(req, &pod, logr.Discard())
	require.True(t, resp.Allowed)
	testutils.AssertWebhookResponse(t, resp.Allowed, resp.Patches, []testutils.ExpectedPatch{
		testutils.AddMetadataLabels(map[string]interface{}{
			"project-id": "proj",
		}),
	})
}
