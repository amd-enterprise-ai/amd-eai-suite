// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';

import { WorkloadStatus, WorkloadType } from '@/types/enums/workloads';
import { Workload } from '@/types/workloads';

import WorkloadLogsModal from '@/components/features/workloads/WorkloadLogsModal';

import wrapper from '@/__tests__/ProviderWrapper';
import { vi } from 'vitest';

// Mock the WorkloadLogs component
vi.mock('@/components/features/workloads/WorkloadLogs', () => ({
  __esModule: true,
  default: vi.fn(({ workload, isOpen }) => {
    if (!workload) {
      return <div>list.actions.logs.modal.workloadNotFound</div>;
    }
    return (
      <div data-testid="workload-logs-component">
        <div>list.actions.logs.modal.description</div>
        <div>Mocked WorkloadLogs Component</div>
        <div>Workload: {workload.name}</div>
        <div>IsOpen: {isOpen ? 'true' : 'false'}</div>
      </div>
    );
  }),
}));

describe('WorkloadLogsModal', () => {
  const mockOnOpenChange = vi.fn();

  const mockWorkload: Workload = {
    id: 'workload-1',
    name: 'Test Workload',
    displayName: 'Test Workload Display',
    status: WorkloadStatus.RUNNING,
    type: WorkloadType.INFERENCE,
    createdAt: '2023-01-01T00:00:00Z',
    updatedAt: '2023-01-01T00:00:00Z',
    createdBy: 'test-user',
    chartId: 'chart-1',
    clusterId: 'cluster-1',
    cluster: {
      id: 'cluster-1',
      name: 'Test Cluster',
      lastHeartbeatAt: '2023-01-01T00:00:00Z',
      status: 'HEALTHY' as any,
    },
    allocatedResources: {
      gpuCount: 1,
      vram: 2147483648.0,
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders modal when open', () => {
    render(
      <WorkloadLogsModal
        workload={mockWorkload}
        isOpen={true}
        onOpenChange={mockOnOpenChange}
      />,
      { wrapper },
    );

    // Check modal title is displayed
    expect(
      screen.getByText('list.actions.logs.modal.title'),
    ).toBeInTheDocument();

    // Check that WorkloadLogs component is rendered
    expect(screen.getByTestId('workload-logs-component')).toBeInTheDocument();
    expect(
      screen.getByText('Mocked WorkloadLogs Component'),
    ).toBeInTheDocument();
    expect(screen.getByText('Workload: Test Workload')).toBeInTheDocument();
    expect(screen.getByText('IsOpen: true')).toBeInTheDocument();

    // Check close button is present
    expect(screen.getByText('actions.close.title')).toBeInTheDocument();
  });

  it('does not render when modal is closed', () => {
    render(
      <WorkloadLogsModal
        workload={mockWorkload}
        isOpen={false}
        onOpenChange={mockOnOpenChange}
      />,
      { wrapper },
    );

    // Modal should not be in the document when closed
    expect(
      screen.queryByText('list.actions.logs.modal.title'),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId('workload-logs-component'),
    ).not.toBeInTheDocument();
  });

  it('handles modal close action', () => {
    render(
      <WorkloadLogsModal
        workload={mockWorkload}
        isOpen={true}
        onOpenChange={mockOnOpenChange}
      />,
      { wrapper },
    );

    // Find and click the close button
    const closeButton = screen.getByText('actions.close.title');
    fireEvent.click(closeButton);

    expect(mockOnOpenChange).toHaveBeenCalledWith(false);
  });

  it('passes correct props to WorkloadLogs component', () => {
    render(
      <WorkloadLogsModal
        workload={mockWorkload}
        isOpen={true}
        onOpenChange={mockOnOpenChange}
      />,
      { wrapper },
    );

    // Verify WorkloadLogs receives correct props
    expect(screen.getByText('Workload: Test Workload')).toBeInTheDocument();
    expect(screen.getByText('IsOpen: true')).toBeInTheDocument();
  });

  it('handles undefined workload', () => {
    render(
      <WorkloadLogsModal
        workload={undefined}
        isOpen={true}
        onOpenChange={mockOnOpenChange}
      />,
      { wrapper },
    );

    // Should still render modal with title
    expect(
      screen.getByText('list.actions.logs.modal.title'),
    ).toBeInTheDocument();

    // WorkloadLogs should handle undefined workload
    expect(
      screen.getByText('list.actions.logs.modal.workloadNotFound'),
    ).toBeInTheDocument();
  });

  it('updates WorkloadLogs when isOpen changes', () => {
    const { rerender } = render(
      <WorkloadLogsModal
        workload={mockWorkload}
        isOpen={true}
        onOpenChange={mockOnOpenChange}
      />,
      { wrapper },
    );

    // Initially open
    expect(screen.getByText('IsOpen: true')).toBeInTheDocument();

    // Close modal
    rerender(
      <WorkloadLogsModal
        workload={mockWorkload}
        isOpen={false}
        onOpenChange={mockOnOpenChange}
      />,
    );

    // Modal should not be rendered when closed
    expect(
      screen.queryByTestId('workload-logs-component'),
    ).not.toBeInTheDocument();
  });

  it('has correct modal configuration', () => {
    render(
      <WorkloadLogsModal
        workload={mockWorkload}
        isOpen={true}
        onOpenChange={mockOnOpenChange}
      />,
      { wrapper },
    );

    // Check modal title
    expect(
      screen.getByText('list.actions.logs.modal.title'),
    ).toBeInTheDocument();

    // Check close button text
    expect(screen.getByText('actions.close.title')).toBeInTheDocument();

    // Verify modal is rendered
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('calls onOpenChange on modal close', () => {
    render(
      <WorkloadLogsModal
        workload={mockWorkload}
        isOpen={true}
        onOpenChange={mockOnOpenChange}
      />,
      { wrapper },
    );

    // Close button should trigger onOpenChange
    const closeButton = screen.getByText('actions.close.title');
    fireEvent.click(closeButton);

    expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    expect(mockOnOpenChange).toHaveBeenCalledTimes(1);
  });
});
