// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package handlers

import (
	"context"
	"errors"
	"testing"

	"github.com/silogen/agent/internal/messaging"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"
)

// mockHandler is a test double for ResourceHandler
type mockHandler struct {
	createCalled bool
	deleteCalled bool
	updateCalled bool
	createErr    error
	deleteErr    error
	updateErr    error
	lastMsg      *messaging.RawMessage
}

func (m *mockHandler) HandleCreate(ctx context.Context, msg *messaging.RawMessage) error {
	m.createCalled = true
	m.lastMsg = msg
	return m.createErr
}

func (m *mockHandler) HandleDelete(ctx context.Context, msg *messaging.RawMessage) error {
	m.deleteCalled = true
	m.lastMsg = msg
	return m.deleteErr
}

func (m *mockHandler) HandleUpdate(ctx context.Context, msg *messaging.RawMessage) error {
	m.updateCalled = true
	m.lastMsg = msg
	return m.updateErr
}

func newTestRouter(namespace, quota, secret ResourceHandler) *Router {
	logger := zap.New()
	return &Router{
		logger:    logger,
		namespace: namespace,
		quota:     quota,
		secret:    secret,
	}
}

func TestRouter_RoutesNamespaceCreate(t *testing.T) {
	mock := &mockHandler{}
	router := newTestRouter(mock, &mockHandler{}, nil)

	msg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectNamespaceCreate,
		Payload: []byte(`{"message_type": "project_namespace_create"}`),
	}

	err := router.Handle(context.Background(), msg)

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !mock.createCalled {
		t.Error("expected HandleCreate to be called")
	}
	if mock.deleteCalled {
		t.Error("HandleDelete should not be called")
	}
	if mock.lastMsg != msg {
		t.Error("handler should receive the same message")
	}
}

func TestRouter_RoutesNamespaceDelete(t *testing.T) {
	mock := &mockHandler{}
	router := newTestRouter(mock, &mockHandler{}, nil)

	msg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectNamespaceDelete,
		Payload: []byte(`{"message_type": "project_namespace_delete"}`),
	}

	err := router.Handle(context.Background(), msg)

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !mock.deleteCalled {
		t.Error("expected HandleDelete to be called")
	}
	if mock.createCalled {
		t.Error("HandleCreate should not be called")
	}
}

func TestRouter_RoutesSecretsCreate(t *testing.T) {
	secretMock := &mockHandler{}
	router := newTestRouter(nil, &mockHandler{}, secretMock)

	msg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectSecretsCreate,
		Payload: []byte(`{"message_type": "project_secrets_create"}`),
	}

	err := router.Handle(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !secretMock.createCalled {
		t.Error("expected secret HandleCreate to be called")
	}
	if secretMock.deleteCalled || secretMock.updateCalled {
		t.Error("expected only HandleCreate to be called for secrets create")
	}
	if secretMock.lastMsg != msg {
		t.Error("handler should receive the same message")
	}
}

func TestRouter_RoutesSecretsDelete(t *testing.T) {
	secretMock := &mockHandler{}
	router := newTestRouter(nil, &mockHandler{}, secretMock)

	msg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectSecretsDelete,
		Payload: []byte(`{"message_type": "project_secrets_delete"}`),
	}

	err := router.Handle(context.Background(), msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !secretMock.deleteCalled {
		t.Error("expected secret HandleDelete to be called")
	}
	if secretMock.createCalled || secretMock.updateCalled {
		t.Error("expected only HandleDelete to be called for secrets delete")
	}
	if secretMock.lastMsg != msg {
		t.Error("handler should receive the same message")
	}
}

func TestRouter_UnknownTypeReturnsNil(t *testing.T) {
	mock := &mockHandler{}
	router := newTestRouter(mock, &mockHandler{}, nil)

	msg := &messaging.RawMessage{
		Type:    "unknown_message_type",
		Payload: []byte(`{"message_type": "unknown_message_type"}`),
	}

	err := router.Handle(context.Background(), msg)

	// Unknown types should not error - just log a warning
	if err != nil {
		t.Fatalf("unexpected error for unknown type: %v", err)
	}
	if mock.createCalled || mock.deleteCalled {
		t.Error("no handler should be called for unknown type")
	}
}

func TestRouter_PropagatesHandlerError(t *testing.T) {
	expectedErr := errors.New("handler error")
	mock := &mockHandler{createErr: expectedErr}
	router := newTestRouter(mock, &mockHandler{}, nil)

	msg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectNamespaceCreate,
		Payload: []byte(`{"message_type": "project_namespace_create"}`),
	}

	err := router.Handle(context.Background(), msg)

	if err != expectedErr {
		t.Errorf("expected error %v, got %v", expectedErr, err)
	}
}

func TestRouter_PropagatesSecretHandlerError(t *testing.T) {
	expectedErr := errors.New("secret handler error")
	secretMock := &mockHandler{deleteErr: expectedErr}
	router := newTestRouter(nil, &mockHandler{}, secretMock)

	msg := &messaging.RawMessage{
		Type:    messaging.MessageTypeProjectSecretsDelete,
		Payload: []byte(`{"message_type": "project_secrets_delete"}`),
	}

	err := router.Handle(context.Background(), msg)
	if err != expectedErr {
		t.Errorf("expected error %v, got %v", expectedErr, err)
	}
}
