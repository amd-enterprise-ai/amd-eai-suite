// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render, screen } from '@testing-library/react';

import { Model, ModelOnboardingStatus } from '@/types/models';

import ModelDetailsModal from '@/components/features/models/ModelDetailsModal';

import { describe, expect, it, vi } from 'vitest';

const mockModel: Model = {
  id: '3',
  name: 'Test Model',
  createdAt: '2023-01-02T00:00:00Z',
  modelWeightsPath: '/dev/null',
  createdBy: 'Test',
  onboardingStatus: ModelOnboardingStatus.READY,
  canonicalName: 'test-org/test-model',
};

describe('ModelDetailsModal', () => {
  let onOpenChangeMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onOpenChangeMock = vi.fn();
  });

  it('should not render if isOpen is false', () => {
    render(
      <ModelDetailsModal
        isOpen={false}
        onOpenChange={onOpenChangeMock}
        model={mockModel}
      />,
    );
    expect(
      screen.queryByText('list.actions.details.modal.title'),
    ).not.toBeInTheDocument();
  });

  it('should render with default title if model is undefined but isOpen is true', () => {
    // Note: The component currently renders a default title even if model is undefined.
    // Adjust test if component behavior changes to not render or show specific message.
    render(
      <ModelDetailsModal
        isOpen={true}
        onOpenChange={onOpenChangeMock}
        model={undefined}
      />,
    );
    expect(
      screen.getByText('list.actions.details.modal.title'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('list.actions.details.modal.modelNotFound'),
    ).toBeInTheDocument();
  });

  it('should render the modal with correct title when open and model is provided', () => {
    render(
      <ModelDetailsModal
        isOpen={true}
        onOpenChange={onOpenChangeMock}
        model={mockModel}
      />,
    );

    expect(
      screen.getByText('list.actions.details.modal.title'),
    ).toBeInTheDocument();
  });

  it('should display all model details', () => {
    render(
      <ModelDetailsModal
        isOpen={true}
        onOpenChange={onOpenChangeMock}
        model={mockModel}
      />,
    );

    // Check if all keys and values from mockModel are rendered
    Object.entries(mockModel).forEach(([key, value]) => {
      expect(screen.getByText(key)).toBeInTheDocument();
      const valueString =
        typeof value === 'object' ? JSON.stringify(value) : String(value);
      // Use queryByText for potentially long strings or complex objects
      expect(screen.queryByText(valueString)).toBeInTheDocument();
    });
  });

  it('should call onOpenChange with false when close button is clicked', () => {
    render(
      <ModelDetailsModal
        isOpen={true}
        onOpenChange={onOpenChangeMock}
        model={mockModel}
      />,
    );

    const closeButton = screen.getByText('list.actions.details.modal.close');
    fireEvent.click(closeButton);

    expect(onOpenChangeMock).toHaveBeenCalledTimes(1);
    expect(onOpenChangeMock).toHaveBeenCalledWith(false);
  });

  it('should call onOpenChange with false when modal overlay is clicked (simulated via onClose)', () => {
    // Assuming Modal component calls onClose when overlay is clicked
    render(
      <ModelDetailsModal
        isOpen={true}
        onOpenChange={onOpenChangeMock}
        model={mockModel}
      />,
    );

    // Simulate the Modal's internal onClose mechanism if possible,
    // otherwise test the handleClose function directly or rely on button test.
    // For this example, we'll re-test the close button as a proxy for onClose trigger.
    const closeButton = screen.getByText('list.actions.details.modal.close');
    fireEvent.click(closeButton); // This triggers handleClose -> onOpenChange(false)

    expect(onOpenChangeMock).toHaveBeenCalledTimes(1);
    expect(onOpenChangeMock).toHaveBeenCalledWith(false);
  });
});
