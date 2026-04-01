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

import router from 'next/router';

import { deleteCluster, fetchClusters } from '@/services/app';

import { gigabytesToBytes } from '@amdenterpriseai/utils/app';

import { Cluster, ClustersResponse } from '@amdenterpriseai/types';
import { ClusterStatus } from '@amdenterpriseai/types';
import { WorkloadsStats } from '@amdenterpriseai/types';

import ClusterPage from '@/pages/clusters';

import wrapper from '@/__tests__/ProviderWrapper';
import '@testing-library/jest-dom';
import { DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA } from '@amdenterpriseai/utils/app';

const extraClusterInfo = {
  lastHeartbeatAt: '2025-03-11T23:24:03.733668Z',
  availableResources: {
    cpuMilliCores: 24000,
    memoryBytes: gigabytesToBytes(25),
    ephemeralStorageBytes: gigabytesToBytes(700),
    gpuCount: 64,
  },
  allocatedResources: {
    cpuMilliCores: 6500,
    memoryBytes: gigabytesToBytes(5),
    ephemeralStorageBytes: gigabytesToBytes(100),
    gpuCount: 12,
  },
  totalNodeCount: 2,
  availableNodeCount: 2,
  assignedQuotaCount: 1,
  gpuInfo: {
    vendor: 'AMD',
    type: '740c',
    name: 'Instinct MI250X',
    memoryBytesPerDevice: gigabytesToBytes(96),
  },
  createdAt: '2025-03-11T23:14:03.733668Z',
  gpuAllocationPercentage: 18.75,
  cpuAllocationPercentage: 27.08,
  memoryAllocationPercentage: 20.0,
};

const generateMockClusters = (
  count: number,
  status: ClusterStatus,
): Cluster[] => {
  return Array.from({ length: count }, (_, i) => ({
    id: (i + 1).toString(),
    name: `Name ${i + 1}`,
    status,
    ...extraClusterInfo,
  }));
};

const mockWorkloadsStats: WorkloadsStats = {
  runningWorkloadsCount: 10,
  pendingWorkloadsCount: 3,
};

const mockClustersResponse: ClustersResponse = {
  data: [],
};

vi.mock('@/services/app', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/services/app')>()),
  fetchClusters: vi.fn(),
  addCluster: vi.fn(),
  deleteCluster: vi.fn(),
  getWorkloadsStats: vi.fn(),
  fetchOrganization: vi.fn().mockResolvedValue({ idpLinked: false }),
}));

describe('clusters', () => {
  it('should not crash the page', async () => {
    let _container: HTMLElement | null = null;
    await act(() => {
      const { container } = render(
        <ClusterPage
          clusters={mockClustersResponse}
          workloadsStats={mockWorkloadsStats}
        />,
        { wrapper },
      );
      _container = container;
    });
    expect(_container).toBeTruthy();
  });

  it('should render a list of clusters', async () => {
    const mockClusters = generateMockClusters(5, ClusterStatus.HEALTHY);
    await act(() => {
      render(
        <ClusterPage
          clusters={{ ...mockClustersResponse, data: mockClusters }}
          workloadsStats={mockWorkloadsStats}
        />,
        { wrapper },
      );
    });

    mockClusters.forEach((cluster) => {
      expect(screen.getByText(cluster.name)).toBeInTheDocument();
    });

    expect(screen.queryByText('list.pending.title')).not.toBeInTheDocument();
  });

  it('should filter the list of clusters based on name', async () => {
    const mockClusters = generateMockClusters(5, ClusterStatus.HEALTHY);
    await act(async () => {
      render(
        <ClusterPage
          clusters={{ ...mockClustersResponse, data: mockClusters }}
          workloadsStats={mockWorkloadsStats}
        />,
        { wrapper },
      );
    });

    await act(() => {
      const filterInput = screen.getByPlaceholderText(
        'list.filter.search.placeholder',
      );
      expect(filterInput).toBeInTheDocument();

      // Simulate user typing in the filter input
      fireEvent.change(filterInput, { target: { value: 'Name 2' } });
    });

    // Check that only the filtered Project is displayed

    await waitFor(() => {
      expect(screen.getByText('Name 2')).toBeInTheDocument();
      expect(screen.queryByText('Name 1')).not.toBeInTheDocument();
      expect(screen.queryByText('Name 3')).not.toBeInTheDocument();
      expect(screen.queryByText('Name 4')).not.toBeInTheDocument();
      expect(screen.queryByText('Name 5')).not.toBeInTheDocument();
    });
  });

  it('should refetch the list of clusters every 10 seconds if any of them have state verifying', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });

    const mockClusters = generateMockClusters(1, ClusterStatus.VERIFYING);
    // Immediately after page load
    vi.mocked(fetchClusters).mockResolvedValueOnce({
      data: generateMockClusters(1, ClusterStatus.VERIFYING),
    });

    // After 10 seconds, still verifying
    vi.mocked(fetchClusters).mockResolvedValueOnce({
      data: generateMockClusters(1, ClusterStatus.VERIFYING),
    });

    // After 20 seconds, healthy
    vi.mocked(fetchClusters).mockResolvedValueOnce({
      data: generateMockClusters(1, ClusterStatus.HEALTHY),
    });

    await act(async () => {
      render(
        <ClusterPage
          clusters={{ ...mockClustersResponse, data: mockClusters }}
          workloadsStats={mockWorkloadsStats}
        />,
        { wrapper },
      );
    });

    // On page load
    expect(fetchClusters).toBeCalledTimes(1);

    // After 10 seconds, get clusters still verifying
    await act(() =>
      vi.advanceTimersByTimeAsync(DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA),
    );
    expect(fetchClusters).toBeCalledTimes(2);

    // After 20 seconds, get clusters again, now healthy
    await act(() =>
      vi.advanceTimersByTimeAsync(DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA),
    );
    expect(fetchClusters).toBeCalledTimes(3);

    // No more polling
    await act(() =>
      vi.advanceTimersByTimeAsync(DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA),
    );
    expect(fetchClusters).toBeCalledTimes(3);

    vi.useRealTimers();
  });

  it('should call deleteClusterAPI if the delete dropdown is clicked and confirmed', async () => {
    const mockClusters = generateMockClusters(5, ClusterStatus.HEALTHY);
    await act(() => {
      render(
        <ClusterPage
          clusters={{ ...mockClustersResponse, data: mockClusters }}
          workloadsStats={mockWorkloadsStats}
        />,
        { wrapper },
      );
    });

    await act(() => {
      const dropDowns = screen.getAllByLabelText('list.actions.label');
      expect(dropDowns).toHaveLength(5);
      // Click the dropdown on cluster 4
      fireEvent.click(dropDowns[3]);
    });

    await act(() => {
      // Click the delete button
      fireEvent.click(screen.getByText('list.actions.delete.label'));
    });
    await act(() => {
      // Confirm the deletion
      fireEvent.click(screen.getByText('actions.confirm.title'));
    });

    await waitFor(() => {
      expect(vi.mocked(deleteCluster)).toHaveBeenCalledWith(
        '4',
        expect.any(Object),
      );
    });
  });

  it('should call bring up edit drawer form for edit', async () => {
    const mockClusters = generateMockClusters(5, ClusterStatus.HEALTHY);
    await act(() => {
      render(
        <ClusterPage
          clusters={{ ...mockClustersResponse, data: mockClusters }}
          workloadsStats={mockWorkloadsStats}
        />,
        { wrapper },
      );
    });

    await act(() => {
      const dropDowns = screen.getAllByLabelText('list.actions.label');
      expect(dropDowns).toHaveLength(5);
      // Click the dropdown on cluster 4
      fireEvent.click(dropDowns[3]);
    });

    await act(() => {
      // Click the edit button
      fireEvent.click(screen.getByText('list.actions.edit.label'));
    });

    await waitFor(() => {
      expect(screen.getByText('form.edit.title')).toBeInTheDocument();
    });
  });

  it('should handle row click', async () => {
    const mockClusters = generateMockClusters(5, ClusterStatus.HEALTHY);

    const mockRouterPush = vi.fn();
    vi.spyOn(router, 'push').mockImplementation(mockRouterPush);

    await act(async () => {
      render(
        <ClusterPage
          clusters={{ ...mockClustersResponse, data: mockClusters }}
          workloadsStats={mockWorkloadsStats}
        />,
        { wrapper },
      );
    });

    await act(() => {
      const row = screen.getByText('Name 2').closest('tr');
      expect(row).toBeInTheDocument();
      fireEvent.click(row!);
    });

    expect(mockRouterPush).toHaveBeenCalledWith('/clusters/2');
  });

  it('show delete a row from the pending clusters table if the actions performed and confirmed', async () => {
    const mockClusters = generateMockClusters(2, ClusterStatus.VERIFYING);
    mockClusters[1].status = ClusterStatus.HEALTHY;

    await act(() => {
      render(
        <ClusterPage
          clusters={{ ...mockClustersResponse, data: mockClusters }}
          workloadsStats={mockWorkloadsStats}
        />,
        { wrapper },
      );
    });

    expect(screen.queryByText('list.pending.title')).toBeInTheDocument();

    await act(() => {
      const dropDowns = screen.getAllByLabelText('list.actions.label');
      expect(dropDowns).toHaveLength(2);
      // Click the dropdown on cluster 2 - the cluster in the pending clusters table
      fireEvent.click(dropDowns[1]);
    });

    await act(() => {
      // Click the delete button
      fireEvent.click(screen.getByText('list.actions.delete.label'));
    });
    await act(() => {
      // Confirm the deletion
      fireEvent.click(screen.getByText('actions.confirm.title'));
    });

    await waitFor(() => {
      expect(vi.mocked(deleteCluster)).toHaveBeenCalledWith(
        '1',
        expect.any(Object),
      );
    });
  });
});
