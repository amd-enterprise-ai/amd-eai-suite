// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

package testutils

import "context"

type MockPublisher struct {
	Published    []interface{}
	PublishError error
}

func NewMockPublisher() *MockPublisher {
	return &MockPublisher{
		Published: make([]interface{}, 0),
	}
}

func NewMockFailingPublisher(error error) *MockPublisher {
	return &MockPublisher{
		PublishError: error,
	}
}

func (m *MockPublisher) Publish(ctx context.Context, message interface{}) error {
	if m.PublishError != nil {
		return m.PublishError
	}
	m.Published = append(m.Published, message)
	return nil
}

func (m *MockPublisher) Connect(ctx context.Context) error { return nil }
func (m *MockPublisher) Close() error                      { return nil }

// MockSelectiveFailingPublisher allows selective failure based on message type.
type MockSelectiveFailingPublisher struct {
	Published    []interface{}
	ShouldFail   func(interface{}) bool
	PublishError error
}

func NewMockSelectiveFailingPublisher(shouldFail func(interface{}) bool, error error) *MockSelectiveFailingPublisher {
	return &MockSelectiveFailingPublisher{
		Published:    make([]interface{}, 0),
		ShouldFail:   shouldFail,
		PublishError: error,
	}
}

func (m *MockSelectiveFailingPublisher) Publish(ctx context.Context, message interface{}) error {
	if m.ShouldFail(message) {
		return m.PublishError
	}
	m.Published = append(m.Published, message)
	return nil
}

func (m *MockSelectiveFailingPublisher) Connect(ctx context.Context) error { return nil }
func (m *MockSelectiveFailingPublisher) Close() error                      { return nil }
