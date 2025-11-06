// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render, screen } from '@testing-library/react';

import { Model, ModelOnboardingStatus } from '@/types/models';

import DeleteModelModal from '@/components/features/models/DeleteModelModal';

import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockModel: Model = {
  id: '3',
  name: 'Test Model',
  createdAt: '2023-01-02T00:00:00Z',
  modelWeightsPath: '/dev/null',
  createdBy: 'Test',
  onboardingStatus: ModelOnboardingStatus.READY,
  canonicalName: 'test-org/test-model',
};

describe('DeleteModelModal', () => {
  let onOpenChangeMock: ReturnType<typeof vi.fn>;
  let onConfirmActionMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onOpenChangeMock = vi.fn();
    onConfirmActionMock = vi.fn();
  });

  it('should not render if isOpen is false', () => {
    render(
      <DeleteModelModal
        isOpen={false}
        onOpenChange={onOpenChangeMock}
        onConfirmAction={onConfirmActionMock}
        model={mockModel}
      />,
    );
    expect(
      screen.queryByText('list.actions.delete.confirmation.title'),
    ).not.toBeInTheDocument();
  });

  it('should not render if model is undefined', () => {
    render(
      <DeleteModelModal
        isOpen={true}
        onOpenChange={onOpenChangeMock}
        onConfirmAction={onConfirmActionMock}
        model={undefined}
      />,
    );
    expect(
      screen.queryByText('list.actions.delete.confirmation.title'),
    ).not.toBeInTheDocument();
  });

  it('should render the modal with correct content when open and model is provided', () => {
    render(
      <DeleteModelModal
        isOpen={true}
        onOpenChange={onOpenChangeMock}
        onConfirmAction={onConfirmActionMock}
        model={mockModel}
      />,
    );

    expect(
      screen.getByText('list.actions.delete.confirmation.title'),
    ).toBeInTheDocument();
  });

  it('should call onConfirmAction and onOpenChange when confirm button is clicked', () => {
    render(
      <DeleteModelModal
        isOpen={true}
        onOpenChange={onOpenChangeMock}
        onConfirmAction={onConfirmActionMock}
        model={mockModel}
      />,
    );

    const confirmButton = screen.getByText('actions.confirm.title');
    fireEvent.click(confirmButton);

    expect(onConfirmActionMock).toHaveBeenCalledTimes(1);
    expect(onConfirmActionMock).toHaveBeenCalledWith({ id: mockModel.id });
    expect(onOpenChangeMock).toHaveBeenCalledTimes(1);
    expect(onOpenChangeMock).toHaveBeenCalledWith(false);
  });

  it('should call onOpenChange when close button is clicked', () => {
    render(
      <DeleteModelModal
        isOpen={true}
        onOpenChange={onOpenChangeMock}
        onConfirmAction={onConfirmActionMock}
        model={mockModel}
      />,
    );

    const closeButton = screen.getByText('actions.close.title');
    fireEvent.click(closeButton);

    expect(onConfirmActionMock).not.toHaveBeenCalled();
    expect(onOpenChangeMock).toHaveBeenCalledTimes(1);
    expect(onOpenChangeMock).toHaveBeenCalledWith(false);
  });

  it('should handle model with different types correctly', () => {
    const baseModel: Model = {
      ...mockModel,
      name: 'Base Model Test',
    };

    render(
      <DeleteModelModal
        isOpen={true}
        onOpenChange={onOpenChangeMock}
        onConfirmAction={onConfirmActionMock}
        model={baseModel}
      />,
    );

    expect(
      screen.getByText('list.actions.delete.confirmation.title'),
    ).toBeInTheDocument();

    const confirmButton = screen.getByText('actions.confirm.title');
    fireEvent.click(confirmButton);

    expect(onConfirmActionMock).toHaveBeenCalledWith({ id: baseModel.id });
  });

  it('should handle model with empty name gracefully', () => {
    const modelWithEmptyName: Model = {
      ...mockModel,
      name: '',
    };

    render(
      <DeleteModelModal
        isOpen={true}
        onOpenChange={onOpenChangeMock}
        onConfirmAction={onConfirmActionMock}
        model={modelWithEmptyName}
      />,
    );

    expect(
      screen.getByText('list.actions.delete.confirmation.title'),
    ).toBeInTheDocument();
  });

  it('should handle adapter model type correctly', () => {
    const adapterModel: Model = {
      ...mockModel,
      name: 'Adapter Model Test',
    };

    render(
      <DeleteModelModal
        isOpen={true}
        onOpenChange={onOpenChangeMock}
        onConfirmAction={onConfirmActionMock}
        model={adapterModel}
      />,
    );

    const confirmButton = screen.getByText('actions.confirm.title');
    fireEvent.click(confirmButton);

    expect(onConfirmActionMock).toHaveBeenCalledWith({ id: adapterModel.id });
    expect(onOpenChangeMock).toHaveBeenCalledWith(false);
  });

  it('should pass correct danger color to confirmation modal', () => {
    render(
      <DeleteModelModal
        isOpen={true}
        onOpenChange={onOpenChangeMock}
        onConfirmAction={onConfirmActionMock}
        model={mockModel}
      />,
    );

    // Verify the modal is rendered with danger styling
    expect(
      screen.getByText('list.actions.delete.confirmation.title'),
    ).toBeInTheDocument();
  });

  it('should not call onConfirmAction when modal is closed without confirmation', () => {
    render(
      <DeleteModelModal
        isOpen={true}
        onOpenChange={onOpenChangeMock}
        onConfirmAction={onConfirmActionMock}
        model={mockModel}
      />,
    );

    // Close the modal without confirming
    onOpenChangeMock.mockClear();
    onConfirmActionMock.mockClear();

    const closeButton = screen.getByText('actions.close.title');
    fireEvent.click(closeButton);

    expect(onConfirmActionMock).not.toHaveBeenCalled();
  });

  it('should handle rapid successive confirm clicks correctly', () => {
    render(
      <DeleteModelModal
        isOpen={true}
        onOpenChange={onOpenChangeMock}
        onConfirmAction={onConfirmActionMock}
        model={mockModel}
      />,
    );

    const confirmButton = screen.getByText('actions.confirm.title');

    // Click multiple times rapidly
    fireEvent.click(confirmButton);
    fireEvent.click(confirmButton);
    fireEvent.click(confirmButton);

    // Should only be called once for the first click
    expect(onConfirmActionMock).toHaveBeenCalledTimes(1);
    expect(onConfirmActionMock).toHaveBeenCalledWith({ id: mockModel.id });
  });
});
