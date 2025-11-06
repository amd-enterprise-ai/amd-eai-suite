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

import { fetchGPUDeviceUtilizationByClusterId } from '@/services/app/metrics';

import { generateMockProjects } from '@/__mocks__/utils/project-mock';

import { Cluster, ClusterNode, ClusterNodesResponse } from '@/types/clusters';
import { ClusterStatus } from '@/types/enums/cluster-status';
import { ClusterProjectsResponse } from '@/types/projects';
import { WorkloadsStats } from '@/types/workloads';

import ClusterPage from '@/pages/clusters/[id]';

import wrapper from '@/__tests__/ProviderWrapper';
import '@testing-library/jest-dom';
import { ProjectStatus } from '@/types/enums/projects';
import { cloneDeep } from 'lodash';
import { getClusterProjects } from '@/services/app/projects';
import { DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA } from '@/utils/app/api-helpers';

const generateMockClusterNodes = (count: number): ClusterNode[] => {
  return Array.from({ length: count }, (_, i) => ({
    id: (i + 1).toString(),
    name: 'gpu-node-' + (i + 1),
    cpuMilliCores: 4000,
    memoryBytes: 26843545600,
    ephemeralStorageBytes: 107374182400,
    gpuCount: 8,
    gpuInfo: {
      vendor: 'AMD',
      type: '740c',
      memoryBytesPerDevice: 68719476736,
      name: 'Instinct MI250X',
    },
    updatedAt: '2025-02-19T10:23:54Z',
    status: 'Ready',
  }));
};

const mockWorkloadsStats: WorkloadsStats = {
  runningWorkloadsCount: 10,
};

vi.mock('@/services/app/workloads', async (importOriginal) => {
  return {
    ...(await importOriginal()),
    getClusterWorkloadsStats: vi.fn(),
  };
});

vi.mock('next/router', () => ({
  useRouter: () => ({
    query: { id: '1' },
    push: vi.fn(),
  }),
}));

vi.mock('@/services/app/metrics', async (importOriginal) => {
  return {
    ...(await importOriginal()),
    fetchGPUDeviceUtilizationByClusterId: vi.fn(),
  };
});

vi.mock('@/services/app/projects', async (importOriginal) => {
  return {
    ...(await importOriginal()),
    getClusterProjects: vi.fn(),
  };
});

const mockClusterNodesResponse: ClusterNodesResponse = {
  clusterNodes: [],
};

const mockProjectsResponse: ClusterProjectsResponse = {
  projects: [],
};

const cluster: Cluster = {
  id: '1',
  name: 'cluster-1',

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

describe('cluster', () => {
  it('should not crash the page', async () => {
    await act(() => {
      const { container } = render(
        <ClusterPage
          cluster={cluster}
          clusterNodesResponse={mockClusterNodesResponse}
          projectsResponse={mockProjectsResponse}
          workloadsStats={mockWorkloadsStats}
        />,
        { wrapper },
      );
      expect(container).toBeTruthy();
    });
  });

  it('should render a list of cluster nodes', async () => {
    const mockClusterNodes = generateMockClusterNodes(5);

    await act(() => {
      render(
        <ClusterPage
          cluster={cluster}
          clusterNodesResponse={{
            clusterNodes: mockClusterNodes,
          }}
          projectsResponse={mockProjectsResponse}
          workloadsStats={mockWorkloadsStats}
        />,
        { wrapper },
      );
    });

    mockClusterNodes.forEach((node) => {
      expect(screen.getAllByText(`${node.cpuMilliCores / 1000}`).length).toBe(
        5,
      );
      expect(screen.getByText(node.name)).toBeInTheDocument();
    });
  });

  it('should filter the list of cluster projects based on name', async () => {
    const mockClusterProjects = generateMockProjects(5);

    await act(async () => {
      render(
        <ClusterPage
          cluster={cluster}
          clusterNodesResponse={mockClusterNodesResponse}
          projectsResponse={{
            projects: mockClusterProjects,
          }}
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
      fireEvent.change(filterInput, { target: { value: 'Project-2' } });
    });

    // Check that only the filtered project is displayed
    await waitFor(() => {
      expect(screen.getByText('project-2')).toBeInTheDocument();
      expect(screen.queryByText('project-1')).not.toBeInTheDocument();
      expect(screen.queryByText('project-3')).not.toBeInTheDocument();
      expect(screen.queryByText('project-4')).not.toBeInTheDocument();
      expect(screen.queryByText('project-5')).not.toBeInTheDocument();
    });
  });

  it('should filter the list of cluster node based on name', async () => {
    const mockClusterNodes = generateMockClusterNodes(5);
    await act(async () => {
      render(
        <ClusterPage
          cluster={cluster}
          clusterNodesResponse={{
            clusterNodes: mockClusterNodes,
          }}
          projectsResponse={mockProjectsResponse}
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
      fireEvent.change(filterInput, { target: { value: 'gpu-node-2' } });
    });
    // Check that only the filtered node is displayed

    await waitFor(() => {
      expect(screen.getByText('gpu-node-2')).toBeInTheDocument();
      expect(screen.queryByText('gpu-node-1')).not.toBeInTheDocument();
      expect(screen.queryByText('gpu-node-3')).not.toBeInTheDocument();
      expect(screen.queryByText('gpu-node-4')).not.toBeInTheDocument();
      expect(screen.queryByText('gpu-node-5')).not.toBeInTheDocument();
    });
  });

  it('should filter the list of cluster node based on gpu-name', async () => {
    const mockClusterNodes = generateMockClusterNodes(5);
    mockClusterNodes[3].gpuInfo = undefined;

    await act(async () => {
      render(
        <ClusterPage
          cluster={cluster}
          clusterNodesResponse={{
            ...mockClusterNodesResponse,
            clusterNodes: mockClusterNodes,
          }}
          projectsResponse={mockProjectsResponse}
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
      fireEvent.change(filterInput, { target: { value: 'MI250X' } });
    });

    // Check that only the filtered nodes are displayed
    await waitFor(() => {
      expect(screen.queryAllByText('Instinct MI250X').length).toBe(4);
      expect(screen.queryByText('gpu-node-4')).not.toBeInTheDocument();
    });
  });

  it('should fetch GPU device utilization data by cluster ID', async () => {
    await act(() => {
      render(
        <ClusterPage
          cluster={cluster}
          clusterNodesResponse={mockClusterNodesResponse}
          projectsResponse={mockProjectsResponse}
          workloadsStats={mockWorkloadsStats}
        />,
        { wrapper },
      );
    });

    expect(fetchGPUDeviceUtilizationByClusterId).toHaveBeenCalledWith(
      '1',
      expect.any(Date),
      expect.any(Date),
    );
  });

  it('should set time range to 24h for GPU device utilization chart', async () => {
    await act(() => {
      render(
        <ClusterPage
          cluster={cluster}
          clusterNodesResponse={mockClusterNodesResponse}
          projectsResponse={mockProjectsResponse}
          workloadsStats={mockWorkloadsStats}
        />,
        { wrapper },
      );
    });

    const tabs = screen.getAllByRole('tab');

    const tab24h = tabs[1];

    expect(tab24h).toBeInTheDocument();

    await act(() => {
      fireEvent.click(tab24h);
    });

    expect(fetchGPUDeviceUtilizationByClusterId).toHaveBeenCalledWith(
      '1',
      expect.any(Date),
      expect.any(Date),
    );
  });

  it('set time range to 7d for chart', async () => {
    await act(() => {
      render(
        <ClusterPage
          cluster={cluster}
          clusterNodesResponse={mockClusterNodesResponse}
          projectsResponse={mockProjectsResponse}
          workloadsStats={mockWorkloadsStats}
        />,
        { wrapper },
      );
    });

    const tabs = screen.getAllByRole('tab');

    const tab7d = tabs[2];

    expect(tab7d).toBeInTheDocument();

    await act(() => {
      fireEvent.click(tab7d);
    });

    expect(fetchGPUDeviceUtilizationByClusterId).toHaveBeenCalledWith(
      '1',
      expect.any(Date),
      expect.any(Date),
    );
  });

  it('refetches the data if project is pending', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const mockProjects = generateMockProjects(1);
    mockProjects[0].status = ProjectStatus.PENDING;

    // Immediately after page load
    vi.mocked(getClusterProjects).mockResolvedValueOnce({
      projects: mockProjects,
    });

    let readyProjects = cloneDeep(mockProjects);
    readyProjects[0].status = ProjectStatus.READY;
    // After 10 seconds, synced
    vi.mocked(getClusterProjects).mockResolvedValueOnce({
      projects: readyProjects,
    });

    await act(async () => {
      render(
        <ClusterPage
          cluster={cluster}
          clusterNodesResponse={mockClusterNodesResponse}
          projectsResponse={mockProjectsResponse}
          workloadsStats={mockWorkloadsStats}
        />,
        {
          wrapper,
        },
      );
    });

    // On page load
    expect(getClusterProjects).toBeCalledTimes(1);

    // After 10 seconds, synced secret
    await act(() =>
      vi.advanceTimersByTimeAsync(DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA),
    );
    expect(getClusterProjects).toBeCalledTimes(2);

    // No more polling
    await act(() =>
      vi.advanceTimersByTimeAsync(DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA),
    );
    expect(getClusterProjects).toBeCalledTimes(2);

    vi.useRealTimers();
  });
});
