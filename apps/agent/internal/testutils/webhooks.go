// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package testutils

import (
	"fmt"
	"testing"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	jsonpatch "gomodules.xyz/jsonpatch/v2"
)

// MatcherFunc matches actual patch values when exact equality is not desired (e.g. UUIDs).
type MatcherFunc func(actual interface{}) bool

// UUIDMatcher returns true if actual parses as a valid UUID (e.g. workload-id, component-id).
var UUIDMatcher MatcherFunc = func(actual interface{}) bool {
	_, err := uuid.Parse(fmt.Sprint(actual))
	return err == nil
}

const (
	opAdd     = "add"
	opReplace = "replace"
)

// JSON pointer path segments for labels and annotations (RFC 6901), so expected paths match patch output exactly.
const (
	LabelSegmentProjectID   = "airm.silogen.ai~1project-id"
	LabelSegmentWorkloadID  = "airm.silogen.ai~1workload-id"
	LabelSegmentComponentID = "airm.silogen.ai~1component-id"
	LabelSegmentKueueName   = "kueue.x-k8s.io~1queue-name"
	LabelSegmentSecretID    = "airm.silogen.ai~1project-secret-id"
	LabelSegmentSecretScope = "airm.silogen.ai~1secret-scope"

	AnnotationSegmentAutoDiscovered = "airm.silogen.ai~1auto-discovered"
	AnnotationSegmentSubmitter      = "airm.silogen.ai~1submitter"
)

type ExpectedPatch struct {
	Operation string
	Path      string
	Value     interface{} // exact value, or MatcherFunc for custom match (e.g. UUIDMatcher)
}

// AssertWebhookResponse requires allowed and that patch count and content match expected (no extra or missing patches).
func AssertWebhookResponse(t *testing.T, allowed bool, actualPatches []jsonpatch.JsonPatchOperation, expectedPatches []ExpectedPatch) {
	t.Helper()
	require.True(t, allowed, "webhook response should be allowed")
	if expectedPatches == nil {
		require.Empty(t, actualPatches, "expected no patches")
		return
	}
	require.Len(t, actualPatches, len(expectedPatches), "patch count should match expected")
	for _, exp := range expectedPatches {
		if !expectedPatchFound(exp, actualPatches) {
			t.Errorf("expected patch not found: op=%s path=%s value=%v\nactual patches: %+v",
				exp.Operation, exp.Path, exp.Value, actualPatches)
		}
	}
}

func expectedPatchFound(exp ExpectedPatch, actualPatches []jsonpatch.JsonPatchOperation) bool {
	for _, p := range actualPatches {
		if p.Path != exp.Path {
			continue
		}
		if p.Operation != exp.Operation && !(exp.Operation == opAdd && p.Operation == opReplace) {
			continue
		}
		if valueMatches(exp.Value, p.Value) {
			return true
		}
	}
	return false
}

func valueMatches(expValue, actualValue interface{}) bool {
	if m, ok := expValue.(MatcherFunc); ok {
		return m(actualValue)
	}
	if expMap, ok := expValue.(map[string]interface{}); ok {
		actualMap, ok := actualValue.(map[string]interface{})
		if !ok || len(actualMap) != len(expMap) {
			return false
		}
		for k, ev := range expMap {
			av, ok := actualMap[k]
			if !ok || !valueMatches(ev, av) {
				return false
			}
		}
		return true
	}
	return assert.ObjectsAreEqual(expValue, actualValue)
}

func AddMetadataLabels(value map[string]interface{}) ExpectedPatch {
	return ExpectedPatch{Operation: opAdd, Path: "/metadata/labels", Value: value}
}

func AddMetadataLabel(key, value string) ExpectedPatch {
	return ExpectedPatch{Operation: opAdd, Path: MetadataLabelsPath(key), Value: value}
}

func AddMetadataLabelMatching(key string, match MatcherFunc) ExpectedPatch {
	return ExpectedPatch{Operation: opAdd, Path: MetadataLabelsPath(key), Value: match}
}

func ReplaceMetadataLabel(key, value string) ExpectedPatch {
	return ExpectedPatch{Operation: opReplace, Path: MetadataLabelsPath(key), Value: value}
}

func AddMetadataAnnotations(value map[string]interface{}) ExpectedPatch {
	return ExpectedPatch{Operation: opAdd, Path: "/metadata/annotations", Value: value}
}

func AddMetadataAnnotation(key, value string) ExpectedPatch {
	return ExpectedPatch{Operation: opAdd, Path: MetadataAnnotationsPath(key), Value: value}
}

func AddPodTemplateLabels(value map[string]interface{}) ExpectedPatch {
	return ExpectedPatch{Operation: opAdd, Path: "/spec/template/metadata/labels", Value: value}
}

func AddPodTemplateLabel(key, value string) ExpectedPatch {
	return ExpectedPatch{Operation: opAdd, Path: PodTemplateLabelsPath(key), Value: value}
}

func AddPodTemplateLabelMatching(key string, match MatcherFunc) ExpectedPatch {
	return ExpectedPatch{Operation: opAdd, Path: PodTemplateLabelsPath(key), Value: match}
}

func AddPatch(path string, value interface{}) ExpectedPatch {
	return ExpectedPatch{Operation: opAdd, Path: path, Value: value}
}

func MetadataLabelsPath(segment string) string {
	return "/metadata/labels/" + segment
}

func MetadataAnnotationsPath(segment string) string {
	return "/metadata/annotations/" + segment
}

func PodTemplateLabelsPath(segment string) string {
	return "/spec/template/metadata/labels/" + segment
}
