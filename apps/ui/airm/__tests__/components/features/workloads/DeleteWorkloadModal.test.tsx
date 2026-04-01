// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen, fireEvent } from '@testing-library/react';

import {
  WorkloadStatus,
  WorkloadType,
  ProjectStatus,
} from '@amdenterpriseai/types';
import type { Workload } from '@amdenterpriseai/types';

import type { WorkloadWithMetrics } from '@/types/workloads';

import DeleteWorkloadModal from '@/components/features/workloads/DeleteWorkloadModal';

import wrapper from '@/__tests__/ProviderWrapper';
import '@testing-library/jest-dom';

vi.mock('next-i18next', async (importOriginal) => {
  const actual = await importOriginal<typeof import('next-i18next')>();
  return {
    ...actual,
    useTranslation: () => ({
      t: (key: string) => key,
      i18n: { language: 'en' },
    }),
  };
});

const mockWorkload: Workload = {
  id: 'wl-001',
  type: WorkloadType.INFERENCE,
  name: 'my-workload',
  displayName: 'My Workload',
  createdBy: 'user@example.com',
  createdAt: '2025-10-01T00:00:00Z',
  updatedAt: '2025-10-01T01:00:00Z',
  status: WorkloadStatus.RUNNING,
  project: {
    id: 'proj-1',
    name: 'test-project',
    description: '',
    status: ProjectStatus.READY,
    statusReason: null,
    clusterId: 'cluster-1',
  },
};

const mockWorkloadWithMetrics: WorkloadWithMetrics = {
  id: 'wl-002',
  projectId: 'proj-1',
  clusterId: 'cluster-1',
  status: WorkloadStatus.RUNNING,
  displayName: 'Metrics Workload',
  type: WorkloadType.FINE_TUNING,
  gpuCount: 4,
  vram: 128,
  createdAt: '2025-10-01T00:00:00Z',
  createdBy: 'user@example.com',
};

describe('DeleteWorkloadModal', () => {
  const onOpenChange = vi.fn();
  const onConfirmAction = vi.fn();

  const setup = (
    workload: Workload | WorkloadWithMetrics | undefined,
    isOpen = true,
  ) =>
    render(
      <DeleteWorkloadModal
        isOpen={isOpen}
        onOpenChange={onOpenChange}
        onConfirmAction={onConfirmAction}
        workload={workload}
      />,
      { wrapper },
    );

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders nothing when workload is undefined', () => {
    const { container } = setup(undefined);
    expect(container.innerHTML).toBe('');
  });

  it('renders modal title and description', () => {
    setup(mockWorkload);
    expect(
      screen.getByText('list.actions.delete.confirmation.title'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('list.actions.delete.confirmation.description'),
    ).toBeInTheDocument();
  });

  it('calls onConfirmAction with workload id on confirm', () => {
    setup(mockWorkload);
    fireEvent.click(screen.getByTestId('confirm-button'));
    expect(onConfirmAction).toHaveBeenCalledWith('wl-001');
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('calls onConfirmAction with id for WorkloadWithMetrics', () => {
    setup(mockWorkloadWithMetrics);
    fireEvent.click(screen.getByTestId('confirm-button'));
    expect(onConfirmAction).toHaveBeenCalledWith('wl-002');
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('calls onOpenChange(false) when close button is clicked', () => {
    setup(mockWorkload);
    fireEvent.click(screen.getByText('actions.close.title'));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
