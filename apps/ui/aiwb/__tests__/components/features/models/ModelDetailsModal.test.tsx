// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render, screen } from '@testing-library/react';

import { AIMModel } from '@/types/aims';

import ModelDetailsModal from '@/components/features/models/ModelDetailsModal';

import { describe, expect, it, vi } from 'vitest';

const mockModel: AIMModel = {
  metadata: {
    name: 'test-model-resource',
    creationTimestamp: '2023-01-02T00:00:00Z',
    labels: {
      'aiwb.apps.eai.amd.com/model-name': 'Test Model',
    },
  },
  spec: {
    profiles: {
      overrides: {
        modelSources: [
          {
            modelId: 'test-org/test-model',
            sourceUri: 'hf://test-org/test-model',
          },
        ],
      },
    },
  },
  status: {
    status: 'Ready',
  },
};

describe('ModelDetailsModal', () => {
  let onOpenChangeMock: ReturnType<typeof vi.fn<(isOpen: boolean) => void>>;

  beforeEach(() => {
    onOpenChangeMock = vi.fn<(isOpen: boolean) => void>();
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

  it('should display model name and resource name', () => {
    render(
      <ModelDetailsModal
        isOpen={true}
        onOpenChange={onOpenChangeMock}
        model={mockModel}
      />,
    );

    expect(screen.getByText('Test Model')).toBeInTheDocument();
    expect(screen.getByText('test-model-resource')).toBeInTheDocument();
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
});
