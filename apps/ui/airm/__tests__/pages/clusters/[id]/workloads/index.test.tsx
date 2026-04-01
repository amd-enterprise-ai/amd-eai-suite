// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, render, screen } from '@testing-library/react';

import {
  fetchClusterWorkloadsMetrics,
  fetchClusterWorkloadsStatusStats,
} from '@/services/app';

import { Cluster } from '@amdenterpriseai/types';
import { ClusterStatus } from '@amdenterpriseai/types';
import { WorkloadStatusStatsResponse } from '@amdenterpriseai/types';

import ClusterWorkloadsPage from '@/pages/clusters/[id]/workloads';

import wrapper from '@/__tests__/ProviderWrapper';
import '@testing-library/jest-dom';
import { Mock } from 'vitest';

const cluster: Cluster = {
  id: '1',
  name: 'test-cluster',
  lastHeartbeatAt: '2025-03-11T23:24:03.733668Z',
  availableResources: {
    cpuMilliCores: 16000,
    memoryBytes: 322122547200,
    ephemeralStorageBytes: 32212254720,
    gpuCount: 8,
  },
  allocatedResources: {
    cpuMilliCores: 6500,
    memoryBytes: 32212254720,
    ephemeralStorageBytes: 21474836480,
    gpuCount: 6,
  },
  totalNodeCount: 2,
  availableNodeCount: 2,
  assignedQuotaCount: 1,
  gpuInfo: {
    vendor: 'AMD',
    type: '740c',
    name: 'Instinct MI250X',
    memoryBytesPerDevice: 68719476736,
  },
  status: ClusterStatus.HEALTHY,
  createdAt: '2025-03-11T23:14:03.733668Z',
  gpuAllocationPercentage: 75.0,
  cpuAllocationPercentage: 40.625,
  memoryAllocationPercentage: 10.0,
};

const mockWorkloadsStatusStats: WorkloadStatusStatsResponse = {
  name: 'test-cluster',
  totalWorkloads: 15,
  statusCounts: [
    { status: 'Running' as any, count: 5 },
    { status: 'Pending' as any, count: 3 },
    { status: 'Complete' as any, count: 7 },
  ],
};

vi.mock('@/services/app', async (importOriginal) => {
  return {
    ...(await importOriginal()),
    fetchClusterWorkloadsMetrics: vi.fn(),
    fetchClusterWorkloadsStatusStats: vi.fn(),
  };
});

const mockPush = vi.fn();

vi.mock('next/router', () => ({
  useRouter: () => ({
    query: { id: '1' },
    push: mockPush,
  }),
}));

describe('cluster workloads page', () => {
  const renderClusterWorkloadsPage = (
    props?: Partial<React.ComponentProps<typeof ClusterWorkloadsPage>>,
  ) => {
    return render(
      <ClusterWorkloadsPage
        cluster={props?.cluster ?? cluster}
        workloadsStatusStats={
          props?.workloadsStatusStats ?? mockWorkloadsStatusStats
        }
        {...props}
      />,
      { wrapper },
    );
  };

  it('should not crash the page', () => {
    const { container } = renderClusterWorkloadsPage();
    expect(container).toBeTruthy();
  });

  it('should render cluster name in header', () => {
    renderClusterWorkloadsPage();
    expect(screen.getAllByText('test-cluster').length).toBeGreaterThan(0);
  });

  it('should render workloads title', () => {
    renderClusterWorkloadsPage();
    expect(screen.getByText('workloads.title')).toBeInTheDocument();
  });

  it('should call fetchClusterWorkloadsStatusStats', () => {
    act(() => {
      renderClusterWorkloadsPage();
    });

    expect(fetchClusterWorkloadsStatusStats as Mock).toHaveBeenCalledWith('1');
  });

  it('should call fetchClusterWorkloadsMetrics', () => {
    act(() => {
      renderClusterWorkloadsPage();
    });

    expect(fetchClusterWorkloadsMetrics as Mock).toHaveBeenCalled();
  });

  it('should have back button that navigates to cluster page', () => {
    renderClusterWorkloadsPage();

    const backButton = screen.getByLabelText('workloads.actions.back');
    expect(backButton).toBeInTheDocument();
  });

  it('should navigate back to cluster page when back button is clicked', async () => {
    await act(() => {
      renderClusterWorkloadsPage();
    });

    const backButton = screen.getByLabelText('workloads.actions.back');
    await act(() => {
      backButton.click();
    });

    expect(mockPush).toHaveBeenCalledWith('/clusters/1');
  });
});
