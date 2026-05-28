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
import { useAccessControl } from '@/hooks/useAccessControl';

import { gigabytesToBytes } from '@amdenterpriseai/utils/app';

import { Cluster } from '@/types/clusters';
import { ClustersResponse } from '@/types/clusters';
import { ClusterStatus } from '@/types/enums/cluster-status';
import { WorkloadsStats } from '@/types/workloads';

import ClusterPage from '@/pages/clusters';

import wrapper from '@/__tests__/ProviderWrapper';
import '@testing-library/jest-dom';
import { DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA } from '@amdenterpriseai/utils/app';

vi.mock('@/hooks/useAccessControl', () => ({
  useAccessControl: vi.fn(),
}));

const adminAccessControl = {
  isRoleManagementEnabled: true,
  isInviteEnabled: true,
  isAdministrator: true,
  smtpEnabled: true,
  isTempPasswordRequired: false,
};

const nonAdminAccessControl = {
  isRoleManagementEnabled: false,
  isInviteEnabled: false,
  isAdministrator: false,
  smtpEnabled: false,
  isTempPasswordRequired: false,
};

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
  workbenchBaseUrl: 'https://workbench.example.com',
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
  beforeEach(() => {
    vi.mocked(useAccessControl).mockReturnValue(adminAccessControl);
  });

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

  it('should show delete action as disabled for non-administrators', async () => {
    vi.mocked(useAccessControl).mockReturnValue(nonAdminAccessControl);
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
      fireEvent.click(dropDowns[3]);
    });

    await waitFor(() => {
      const deleteButton = screen.getByText('list.actions.delete.label');
      expect(
        deleteButton.closest('[data-disabled="true"]'),
      ).toBeInTheDocument();
    });
  });

  it('should show edit action as disabled for non-administrators', async () => {
    vi.mocked(useAccessControl).mockReturnValue(nonAdminAccessControl);
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
      fireEvent.click(dropDowns[3]);
    });

    await waitFor(() => {
      const editButton = screen.getByText('list.actions.edit.label');
      expect(editButton.closest('[data-disabled="true"]')).toBeInTheDocument();
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

  it('should not show pending clusters table for non-administrators', async () => {
    vi.mocked(useAccessControl).mockReturnValue(nonAdminAccessControl);
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

    expect(screen.queryByText('list.pending.title')).not.toBeInTheDocument();
  });

  it('should navigate to cluster details when "Open details" action is clicked', async () => {
    const mockClusters = generateMockClusters(5, ClusterStatus.HEALTHY);
    const mockRouterPush = vi.fn();
    vi.spyOn(router, 'push').mockImplementation(mockRouterPush);

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
      fireEvent.click(dropDowns[2]);
    });

    await act(() => {
      fireEvent.click(screen.getByText('list.actions.openDetails.label'));
    });

    expect(mockRouterPush).toHaveBeenCalledWith('/clusters/3');
  });

  it('should open external URL when "View in AI Workbench" action is clicked', async () => {
    const mockClusters = generateMockClusters(5, ClusterStatus.HEALTHY);
    const mockWindowOpen = vi.fn();
    vi.spyOn(window, 'open').mockImplementation(mockWindowOpen);

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
      fireEvent.click(dropDowns[0]);
    });

    await act(() => {
      fireEvent.click(screen.getByText('list.actions.viewInAiwb.label'));
    });

    expect(mockWindowOpen).toHaveBeenCalledWith(
      'https://workbench.example.com',
      '_blank',
      'noopener,noreferrer',
    );
  });

  it('should show "View in AI Workbench" action as disabled when workbenchBaseUrl is missing', async () => {
    const mockClusters = generateMockClusters(5, ClusterStatus.HEALTHY);
    mockClusters[0].workbenchBaseUrl = undefined;

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
      fireEvent.click(dropDowns[0]);
    });

    await waitFor(() => {
      const viewInAiwbButton = screen.getByText(
        'list.actions.viewInAiwb.label',
      );
      expect(
        viewInAiwbButton.closest('[data-disabled="true"]'),
      ).toBeInTheDocument();
    });
  });

  it('should show "View in AI Workbench" action as disabled when workbenchBaseUrl has invalid scheme', async () => {
    const mockClusters = generateMockClusters(5, ClusterStatus.HEALTHY);
    mockClusters[0].workbenchBaseUrl = 'ftp://invalid.example.com';

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
      fireEvent.click(dropDowns[0]);
    });

    await waitFor(() => {
      const viewInAiwbButton = screen.getByText(
        'list.actions.viewInAiwb.label',
      );
      expect(
        viewInAiwbButton.closest('[data-disabled="true"]'),
      ).toBeInTheDocument();
    });
  });

  it('should call deleteCluster API when delete action is clicked and confirmed by administrator', async () => {
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
      fireEvent.click(dropDowns[3]);
    });

    await act(() => {
      fireEvent.click(screen.getByText('list.actions.delete.label'));
    });

    await act(() => {
      fireEvent.click(screen.getByText('actions.confirm.title'));
    });

    await waitFor(() => {
      expect(vi.mocked(deleteCluster)).toHaveBeenCalledWith(
        '4',
        expect.any(Object),
      );
    });
  });

  it('should open edit drawer form when edit action is clicked by administrator', async () => {
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
      fireEvent.click(dropDowns[3]);
    });

    await act(() => {
      fireEvent.click(screen.getByText('list.actions.edit.label'));
    });

    await waitFor(() => {
      expect(screen.getByText('form.edit.title')).toBeInTheDocument();
    });
  });

  it('should show pending clusters table for administrators', async () => {
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
  });
});
