// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package common

import (
	"context"
	"testing"

	"github.com/stretchr/testify/assert"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	"sigs.k8s.io/controller-runtime/pkg/event"
)

const testFinalizer = "example.com/test-finalizer"

func TestManagedNamespaceEventFilter(t *testing.T) {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)
	_ = appsv1.AddToScheme(scheme)

	t.Run("allows resource in namespace with project-id label", func(t *testing.T) {
		ns := &corev1.Namespace{
			ObjectMeta: metav1.ObjectMeta{
				Name: "managed-namespace",
				Labels: map[string]string{
					ProjectIDLabel: "project-123",
				},
			},
		}

		deployment := &appsv1.Deployment{
			ObjectMeta: metav1.ObjectMeta{
				Name:      "test-deployment",
				Namespace: "managed-namespace",
			},
		}

		client := fake.NewClientBuilder().WithScheme(scheme).WithObjects(ns).Build()

		filter := ManagedNamespaceEventFilter(client)
		result := filter.Create(event.CreateEvent{Object: deployment})

		assert.True(t, result, "should allow resource in managed namespace")
	})

	t.Run("blocks resource in namespace without project-id label", func(t *testing.T) {
		ns := &corev1.Namespace{
			ObjectMeta: metav1.ObjectMeta{
				Name: "unmanaged-namespace",
				Labels: map[string]string{
					"other-label": "other-value",
				},
			},
		}

		deployment := &appsv1.Deployment{
			ObjectMeta: metav1.ObjectMeta{
				Name:      "test-deployment",
				Namespace: "unmanaged-namespace",
			},
		}

		client := fake.NewClientBuilder().WithScheme(scheme).WithObjects(ns).Build()

		filter := ManagedNamespaceEventFilter(client)
		result := filter.Create(event.CreateEvent{Object: deployment})

		assert.False(t, result, "should block resource in unmanaged namespace")
	})

	t.Run("blocks resource when namespace does not exist", func(t *testing.T) {
		deployment := &appsv1.Deployment{
			ObjectMeta: metav1.ObjectMeta{
				Name:      "test-deployment",
				Namespace: "non-existent-namespace",
			},
		}

		client := fake.NewClientBuilder().WithScheme(scheme).Build()

		filter := ManagedNamespaceEventFilter(client)
		result := filter.Create(event.CreateEvent{Object: deployment})

		assert.False(t, result, "should block resource when namespace does not exist")
	})
}

func TestAddFinalizerIfNeeded(t *testing.T) {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)

	t.Run("adds finalizer when not present", func(t *testing.T) {
		pod := &corev1.Pod{
			ObjectMeta: metav1.ObjectMeta{
				Name:      "test-pod",
				Namespace: "test-namespace",
			},
		}
		c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(pod).Build()

		err := AddFinalizerIfNeeded(context.Background(), c, pod, testFinalizer)

		assert.NoError(t, err)
		assert.True(t, controllerutil.ContainsFinalizer(pod, testFinalizer))
	})

	t.Run("does not duplicate finalizer", func(t *testing.T) {
		pod := &corev1.Pod{
			ObjectMeta: metav1.ObjectMeta{
				Name:       "test-pod",
				Namespace:  "test-namespace",
				Finalizers: []string{testFinalizer},
			},
		}
		c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(pod).Build()

		err := AddFinalizerIfNeeded(context.Background(), c, pod, testFinalizer)

		assert.NoError(t, err)
		assert.True(t, controllerutil.ContainsFinalizer(pod, testFinalizer))
		assert.Len(t, pod.GetFinalizers(), 1)
	})
}

func TestRemoveFinalizer(t *testing.T) {
	scheme := runtime.NewScheme()
	_ = corev1.AddToScheme(scheme)

	t.Run("removes finalizer when present", func(t *testing.T) {
		pod := &corev1.Pod{
			ObjectMeta: metav1.ObjectMeta{
				Name:       "test-pod",
				Namespace:  "test-namespace",
				Finalizers: []string{testFinalizer},
			},
		}
		c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(pod).Build()

		err := RemoveFinalizer(context.Background(), c, pod, testFinalizer)

		assert.NoError(t, err)
		assert.False(t, controllerutil.ContainsFinalizer(pod, testFinalizer))
	})

	t.Run("no-op when finalizer not present", func(t *testing.T) {
		pod := &corev1.Pod{
			ObjectMeta: metav1.ObjectMeta{
				Name:       "test-pod",
				Namespace:  "test-namespace",
				Finalizers: []string{"other-finalizer"},
			},
		}
		c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(pod).Build()

		err := RemoveFinalizer(context.Background(), c, pod, testFinalizer)

		assert.NoError(t, err)
		assert.True(t, controllerutil.ContainsFinalizer(pod, "other-finalizer"))
	})

	t.Run("removes only the specified finalizer", func(t *testing.T) {
		pod := &corev1.Pod{
			ObjectMeta: metav1.ObjectMeta{
				Name:       "test-pod",
				Namespace:  "test-namespace",
				Finalizers: []string{testFinalizer, "other-finalizer"},
			},
		}
		c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(pod).Build()

		err := RemoveFinalizer(context.Background(), c, pod, testFinalizer)

		assert.NoError(t, err)
		assert.False(t, controllerutil.ContainsFinalizer(pod, testFinalizer))
		assert.True(t, controllerutil.ContainsFinalizer(pod, "other-finalizer"))
	})
}
