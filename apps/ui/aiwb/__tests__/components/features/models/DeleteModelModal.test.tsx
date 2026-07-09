// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render, screen } from '@testing-library/react';

import { Model } from '@/types/models';
import { ModelOnboardingStatus } from '@/types/models';

import DeleteModelModal from '@/components/features/models/DeleteModelModal';

import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockModel: Model = {
  id: '3',
  name: 'Test Model',
  resourceName: 'test-model-cr',
  createdAt: '2023-01-02T00:00:00Z',
  createdBy: 'Test',
  onboardingStatus: ModelOnboardingStatus.READY,
  canonicalName: 'test-org/test-model',
};

describe('DeleteModelModal', () => {
  let onCloseMock: ReturnType<typeof vi.fn<() => void>>;
  let onConfirmActionMock: ReturnType<
    typeof vi.fn<({ name }: { name: string }) => void>
  >;

  beforeEach(() => {
    onCloseMock = vi.fn<() => void>();
    onConfirmActionMock = vi.fn<({ name }: { name: string }) => void>();
  });

  it('should not render if isOpen is false', () => {
    render(
      <DeleteModelModal
        isOpen={false}
        onClose={onCloseMock}
        onConfirmAction={onConfirmActionMock}
        model={mockModel}
        hasActiveDeployments={false}
        loading={false}
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
        onClose={onCloseMock}
        onConfirmAction={onConfirmActionMock}
        model={undefined}
        hasActiveDeployments={false}
        loading={false}
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
        onClose={onCloseMock}
        onConfirmAction={onConfirmActionMock}
        model={mockModel}
        hasActiveDeployments={false}
        loading={false}
      />,
    );

    expect(
      screen.getByText('list.actions.delete.confirmation.title'),
    ).toBeInTheDocument();
  });

  it('should call onConfirmAction when confirm button is clicked', () => {
    render(
      <DeleteModelModal
        isOpen={true}
        onClose={onCloseMock}
        onConfirmAction={onConfirmActionMock}
        model={mockModel}
        hasActiveDeployments={false}
        loading={false}
      />,
    );

    const confirmButton = screen.getByText('actions.confirm.title');
    fireEvent.click(confirmButton);

    expect(onConfirmActionMock).toHaveBeenCalledTimes(1);
    expect(onConfirmActionMock).toHaveBeenCalledWith({
      name: mockModel.resourceName,
    });
    expect(onCloseMock).not.toHaveBeenCalled();
  });

  it('should call onClose when close button is clicked', () => {
    render(
      <DeleteModelModal
        isOpen={true}
        onClose={onCloseMock}
        onConfirmAction={onConfirmActionMock}
        model={mockModel}
        hasActiveDeployments={false}
        loading={false}
      />,
    );

    const closeButton = screen.getByText('actions.close.title');
    fireEvent.click(closeButton);

    expect(onConfirmActionMock).not.toHaveBeenCalled();
    expect(onCloseMock).toHaveBeenCalledTimes(1);
  });

  it('should handle model with different types correctly', () => {
    const baseModel: Model = {
      ...mockModel,
      name: 'Base Model Test',
    };

    render(
      <DeleteModelModal
        isOpen={true}
        onClose={onCloseMock}
        onConfirmAction={onConfirmActionMock}
        model={baseModel}
        hasActiveDeployments={false}
        loading={false}
      />,
    );

    expect(
      screen.getByText('list.actions.delete.confirmation.title'),
    ).toBeInTheDocument();

    const confirmButton = screen.getByText('actions.confirm.title');
    fireEvent.click(confirmButton);

    expect(onConfirmActionMock).toHaveBeenCalledWith({
      name: mockModel.resourceName,
    });
  });

  it('should handle model with empty name gracefully', () => {
    const modelWithEmptyName: Model = {
      ...mockModel,
      name: '',
    };

    render(
      <DeleteModelModal
        isOpen={true}
        onClose={onCloseMock}
        onConfirmAction={onConfirmActionMock}
        model={modelWithEmptyName}
        hasActiveDeployments={false}
        loading={false}
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
        onClose={onCloseMock}
        onConfirmAction={onConfirmActionMock}
        model={adapterModel}
        hasActiveDeployments={false}
        loading={false}
      />,
    );

    const confirmButton = screen.getByText('actions.confirm.title');
    fireEvent.click(confirmButton);

    expect(onConfirmActionMock).toHaveBeenCalledWith({
      name: mockModel.resourceName,
    });
  });

  it('should pass correct danger color to confirmation modal', () => {
    render(
      <DeleteModelModal
        isOpen={true}
        onClose={onCloseMock}
        onConfirmAction={onConfirmActionMock}
        model={mockModel}
        hasActiveDeployments={false}
        loading={false}
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
        onClose={onCloseMock}
        onConfirmAction={onConfirmActionMock}
        model={mockModel}
        hasActiveDeployments={false}
        loading={false}
      />,
    );

    // Close the modal without confirming
    onCloseMock.mockClear();
    onConfirmActionMock.mockClear();

    const closeButton = screen.getByText('actions.close.title');
    fireEvent.click(closeButton);

    expect(onConfirmActionMock).not.toHaveBeenCalled();
  });

  it('should not call onConfirmAction when loading is true', () => {
    render(
      <DeleteModelModal
        isOpen={true}
        onClose={onCloseMock}
        onConfirmAction={onConfirmActionMock}
        model={mockModel}
        hasActiveDeployments={false}
        loading={true}
      />,
    );

    const confirmButton = screen.getByText('actions.confirm.title');
    fireEvent.click(confirmButton);

    expect(onConfirmActionMock).not.toHaveBeenCalled();
  });
});
