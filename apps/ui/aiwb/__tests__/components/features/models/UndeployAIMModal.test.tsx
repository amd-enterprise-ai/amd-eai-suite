// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen, fireEvent } from '@testing-library/react';
import UndeployAIMModal from '@/components/features/models/UndeployAIMModal';

vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: any) => key,
  }),
  Trans: ({ children }: any) => <>{children}</>,
}));

describe('UndeployAIMModal', () => {
  let mockOnOpenChange: (isOpen: boolean) => void;
  let mockOnConfirmAction: (namespace: string, serviceId: string) => void;

  const defaultProps = {
    isOpen: true,
    onOpenChange: vi.fn(),
    onConfirmAction: vi.fn(),
    serviceToUndeploy: {
      namespace: 'test-namespace',
      serviceId: 'service-123',
      displayName: 'test-model-deployment',
    },
  };

  beforeEach(() => {
    mockOnOpenChange = vi.fn();
    mockOnConfirmAction = vi.fn();
    vi.clearAllMocks();
  });

  it('does not render when serviceToUndeploy is undefined', () => {
    const { container } = render(
      <UndeployAIMModal
        isOpen={true}
        onOpenChange={mockOnOpenChange}
        onConfirmAction={mockOnConfirmAction}
        serviceToUndeploy={undefined}
      />,
    );

    expect(container.firstChild).toBeNull();
  });

  it('does not render modal content when isOpen is false', () => {
    render(
      <UndeployAIMModal
        {...defaultProps}
        isOpen={false}
        onOpenChange={mockOnOpenChange}
        onConfirmAction={mockOnConfirmAction}
      />,
    );

    // Modal should not display content when closed
    expect(screen.queryByText('confirmation.title')).not.toBeInTheDocument();
  });

  it('renders modal with title when open', () => {
    render(
      <UndeployAIMModal
        {...defaultProps}
        onOpenChange={mockOnOpenChange}
        onConfirmAction={mockOnConfirmAction}
      />,
    );

    expect(screen.getByText('confirmation.title')).toBeInTheDocument();
  });

  it('calls onConfirmAction with correct parameters when confirmed', () => {
    render(
      <UndeployAIMModal
        {...defaultProps}
        onOpenChange={mockOnOpenChange}
        onConfirmAction={mockOnConfirmAction}
      />,
    );

    const confirmButton = screen.getByText('actions.confirm.title');
    fireEvent.click(confirmButton);

    expect(mockOnConfirmAction).toHaveBeenCalledWith(
      defaultProps.serviceToUndeploy.namespace,
      defaultProps.serviceToUndeploy.serviceId,
    );
    expect(mockOnConfirmAction).toHaveBeenCalledTimes(1);
  });

  it('closes modal after confirmation', () => {
    render(
      <UndeployAIMModal
        {...defaultProps}
        onOpenChange={mockOnOpenChange}
        onConfirmAction={mockOnConfirmAction}
      />,
    );

    const confirmButton = screen.getByText('actions.confirm.title');
    fireEvent.click(confirmButton);

    expect(mockOnOpenChange).toHaveBeenCalledWith(false);
  });

  it('calls onOpenChange when close button is clicked', () => {
    render(
      <UndeployAIMModal
        {...defaultProps}
        onOpenChange={mockOnOpenChange}
        onConfirmAction={mockOnConfirmAction}
      />,
    );

    const closeButton = screen.getByText('actions.close.title');
    fireEvent.click(closeButton);

    expect(mockOnConfirmAction).not.toHaveBeenCalled();
    expect(mockOnOpenChange).toHaveBeenCalledWith(false);
  });

  it('resets loading state when modal closes', () => {
    const { rerender } = render(
      <UndeployAIMModal
        {...defaultProps}
        onOpenChange={mockOnOpenChange}
        onConfirmAction={mockOnConfirmAction}
      />,
    );

    // Close the modal
    rerender(
      <UndeployAIMModal
        {...defaultProps}
        isOpen={false}
        onOpenChange={mockOnOpenChange}
        onConfirmAction={mockOnConfirmAction}
      />,
    );

    // Reopen the modal
    rerender(
      <UndeployAIMModal
        {...defaultProps}
        isOpen={true}
        onOpenChange={mockOnOpenChange}
        onConfirmAction={mockOnConfirmAction}
      />,
    );

    // Modal should render correctly
    expect(screen.getByText('confirmation.title')).toBeInTheDocument();
  });

  it('handles different service information', () => {
    const customProps = {
      ...defaultProps,
      serviceToUndeploy: {
        namespace: 'custom-namespace',
        serviceId: 'custom-service-id',
        displayName: 'my-custom-deployment-name',
      },
    };

    render(
      <UndeployAIMModal
        {...customProps}
        onOpenChange={mockOnOpenChange}
        onConfirmAction={mockOnConfirmAction}
      />,
    );

    expect(screen.getByText('confirmation.title')).toBeInTheDocument();
  });

  it('prevents multiple rapid confirm clicks', () => {
    render(
      <UndeployAIMModal
        {...defaultProps}
        onOpenChange={mockOnOpenChange}
        onConfirmAction={mockOnConfirmAction}
      />,
    );

    const confirmButton = screen.getByText('actions.confirm.title');

    // Click multiple times
    fireEvent.click(confirmButton);
    fireEvent.click(confirmButton);
    fireEvent.click(confirmButton);

    // Should only trigger once due to internal loading state
    expect(mockOnConfirmAction).toHaveBeenCalledTimes(1);
  });
});
