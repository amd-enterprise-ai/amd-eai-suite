// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package httproute

import (
	"context"
	"testing"

	"github.com/google/uuid"
	agent "github.com/silogen/agent/internal/common"
	"github.com/stretchr/testify/assert"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	"sigs.k8s.io/controller-runtime/pkg/reconcile"
	gatewayv1 "sigs.k8s.io/gateway-api/apis/v1"

	"github.com/silogen/agent/internal/messaging"
	"github.com/silogen/agent/internal/testutils"
	"github.com/silogen/agent/internal/workloads/common"
)

func createTestHTTPRoute(name, namespace string, labels map[string]string) *gatewayv1.HTTPRoute {
	return &gatewayv1.HTTPRoute{
		ObjectMeta: metav1.ObjectMeta{
			Name:      name,
			Namespace: namespace,
			Labels:    labels,
		},
	}
}

func TestReconcile_AddsFinalizer(t *testing.T) {
	scheme := runtime.NewScheme()
	_ = gatewayv1.Install(scheme)

	httpRoute := createTestHTTPRoute("test-httproute", "test-namespace", map[string]string{
		common.WorkloadIDLabel:  uuid.New().String(),
		common.ComponentIDLabel: uuid.New().String(),
		agent.ProjectIDLabel:    uuid.New().String(),
	})

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(httpRoute).Build()
	r := &Reconciler{Client: c, Publisher: testutils.NewMockPublisher()}

	result, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: httpRoute.Name, Namespace: httpRoute.Namespace},
	})

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)

	var updated gatewayv1.HTTPRoute
	_ = c.Get(context.Background(), types.NamespacedName{Name: httpRoute.Name, Namespace: httpRoute.Namespace}, &updated)
	assert.True(t, controllerutil.ContainsFinalizer(&updated, common.WorkloadFinalizer))
}

func TestReconcile_HandlesDeletion(t *testing.T) {
	scheme := runtime.NewScheme()
	_ = gatewayv1.Install(scheme)

	workloadID := uuid.New()
	now := metav1.Now()

	httpRoute := createTestHTTPRoute("test-httproute", "test-namespace", map[string]string{
		common.WorkloadIDLabel:  workloadID.String(),
		common.ComponentIDLabel: uuid.New().String(),
		agent.ProjectIDLabel:    uuid.New().String(),
	})
	httpRoute.SetDeletionTimestamp(&now)
	httpRoute.SetFinalizers([]string{common.WorkloadFinalizer})

	c := fake.NewClientBuilder().WithScheme(scheme).WithObjects(httpRoute).Build()
	mock := testutils.NewMockPublisher()
	r := &Reconciler{Client: c, Publisher: mock}

	result, err := r.Reconcile(context.Background(), reconcile.Request{
		NamespacedName: types.NamespacedName{Name: httpRoute.Name, Namespace: httpRoute.Namespace},
	})

	assert.NoError(t, err)
	assert.Equal(t, ctrl.Result{}, result)
	assert.Len(t, mock.Published, 1)

	msg, ok := mock.Published[0].(messaging.WorkloadComponentStatusMessage)
	assert.True(t, ok)
	assert.Equal(t, "test-httproute", msg.Name)
	assert.Equal(t, "Deleted", msg.Status)
	assert.Equal(t, workloadID.String(), msg.WorkloadID)
}
