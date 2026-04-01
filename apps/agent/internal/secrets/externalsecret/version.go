// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package externalsecret

import (
	"context"
	"fmt"

	"github.com/silogen/agent/internal/kubernetes"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/client-go/dynamic"
)

// DiscoverExternalSecretVersion discovers the ExternalSecret API version from the CRD
//
// It returns:
// - version: discovered version (non-empty) if CRD is installed and valid
// - crdInstalled: true if CRD was found and readable
// - error:
//   - nil if CRD is not installed (404)
//   - non-nil if CRD exists but the version cannot be determined, or on other API errors
func DiscoverExternalSecretVersion(ctx context.Context, dynamicClient dynamic.Interface) (string, bool, error) {
	if dynamicClient == nil {
		return "", false, fmt.Errorf("dynamic client is nil")
	}

	v, err := getExternalSecretVersionFromCRD(ctx, dynamicClient)
	if err != nil {
		if apierrors.IsNotFound(err) {
			return "", false, nil
		}
		return "", false, err
	}
	if v == "" {
		return "", true, fmt.Errorf("ExternalSecret CRD found but no served/storage version could be determined (%s)", crdName)
	}
	return v, true, nil
}

func getExternalSecretVersionFromCRD(ctx context.Context, dynamicClient dynamic.Interface) (string, error) {
	crd, err := dynamicClient.Resource(kubernetes.CRDGVR).Get(ctx, crdName, metav1.GetOptions{})
	if err != nil {
		return "", err
	}

	versions, found, err := unstructured.NestedSlice(crd.Object, "spec", "versions")
	if err != nil || !found || len(versions) == 0 {
		return "", nil
	}

	if storage := findCRDStorageVersion(versions); storage != "" {
		return storage, nil
	}
	return findCRDServedVersion(versions), nil
}

func findCRDStorageVersion(versions []interface{}) string {
	for _, v := range versions {
		name, _, storage, ok := parseCRDVersionEntry(v)
		if ok && storage && name != "" {
			return name
		}
	}
	return ""
}

func findCRDServedVersion(versions []interface{}) string {
	for _, v := range versions {
		name, served, _, ok := parseCRDVersionEntry(v)
		if ok && served && name != "" {
			return name
		}
	}
	return ""
}

func parseCRDVersionEntry(v interface{}) (name string, served bool, storage bool, ok bool) {
	m, ok := v.(map[string]interface{})
	if !ok {
		return "", false, false, false
	}

	name, _, nameErr := unstructured.NestedString(m, "name")
	served, _, servedErr := unstructured.NestedBool(m, "served")
	storage, _, storageErr := unstructured.NestedBool(m, "storage")
	if nameErr != nil || servedErr != nil || storageErr != nil {
		return "", false, false, false
	}
	return name, served, storage, true
}
