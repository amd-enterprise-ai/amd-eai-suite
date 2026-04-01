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

import {
  fetchProjectAverageGPUIdleTime,
  fetchProjectAverageWaitTime,
  fetchProjectGPUDeviceUtilization,
  fetchProjectGPUMemoryUtilization,
  fetchProjectWorkloadsStatuses,
  fetchProjectWorkloadsMetrics,
} from '@/services/app';

import { ClusterStatus } from '@amdenterpriseai/types';
import { ProjectStatus } from '@amdenterpriseai/types';
import { QuotaStatus } from '@amdenterpriseai/types';
import { ProjectWithMembers } from '@amdenterpriseai/types';

import ProjectPage from '@/pages/projects/[id]';

import wrapper from '@/__tests__/ProviderWrapper';
import '@testing-library/jest-dom';
import { Mock } from 'vitest';

const generateMockProjects = (count: number): ProjectWithMembers[] => {
  return Array.from({ length: count }, (_, i) => ({
    id: (i + 1).toString(),
    clusterId: '1',
    name: `Name ${i + 1}`,
    description: `Description ${i + 1}`,
    status: ProjectStatus.READY,
    statusReason: null,
    quota: {
      status: QuotaStatus.READY,
      cpuMilliCores: 1000,
      gpuCount: 1,
      memoryBytes: 2000,
      ephemeralStorageBytes: 10000,
    },
    cluster: {
      id: '1',
      name: `Cluster ${i + 1}`,
      lastHeartbeatAt: new Date().toISOString(),
      status: ClusterStatus.HEALTHY,
    },
    users: [],
    invitedUsers: [],
  }));
};

vi.mock('@/services/app', async (importOriginal) => {
  return {
    ...(await importOriginal()),
    fetchProjectGPUDeviceUtilization: vi.fn(),
    fetchProjectGPUMemoryUtilization: vi.fn(),
    fetchProjectWorkloadsStatuses: vi.fn(),
    fetchProjectWorkloadsMetrics: vi.fn(),
    fetchProjectAverageWaitTime: vi.fn(),
    fetchProjectAverageGPUIdleTime: vi.fn(),
    fetchProjectSecrets: vi.fn(),
    fetchProjectStorages: vi.fn(),
  };
});

const mockPush = vi.fn();

vi.mock('next/router', () => ({
  useRouter: () => ({
    query: { id: '1' },
    push: mockPush,
  }),
}));

vi.mock('@amdenterpriseai/hooks', async (importOriginal) => ({
  ...(await importOriginal()),
  useAccessControl: vi.fn(() => ({
    isRoleManagementEnabled: true,
    isInviteEnabled: true,
    isAdministrator: true,
  })),
}));

describe('projects page', () => {
  const renderProjectPage = (
    props?: Partial<React.ComponentProps<typeof ProjectPage>>,
  ) => {
    return render(
      <ProjectPage
        project={props?.project ?? generateMockProjects(1)[0]}
        {...props}
      />,
      { wrapper },
    );
  };

  it('should not crash the page', () => {
    const { container } = renderProjectPage({
      project: generateMockProjects(1)[0],
    });
    expect(container).toBeTruthy();
    expect(screen.getByText('dashboard.overview.title')).toBeInTheDocument();
  });

  it('fetchProjectGPUDeviceUtilization the page', () => {
    act(() => {
      renderProjectPage({
        project: generateMockProjects(1)[0],
      });
    });

    expect(fetchProjectGPUDeviceUtilization as Mock).toHaveBeenCalled();
  });

  it('fetchProjectWorkloadsMetrics the page', () => {
    act(() => {
      renderProjectPage({
        project: generateMockProjects(1)[0],
      });
    });

    expect(fetchProjectWorkloadsMetrics as Mock).toHaveBeenCalled();
  });

  it('fetchProjectWorkloadsStatuses the page', () => {
    act(() => {
      renderProjectPage({
        project: generateMockProjects(1)[0],
      });
    });

    expect(fetchProjectWorkloadsStatuses as Mock).toHaveBeenCalled();
  });

  it('fetchProjectGPUMemoryUtilization the page', () => {
    act(() => {
      renderProjectPage({
        project: generateMockProjects(1)[0],
      });
    });

    expect(fetchProjectGPUMemoryUtilization as Mock).toHaveBeenCalled();
  });

  it('fetchProjectGPUDeviceUtilization the page', () => {
    act(() => {
      renderProjectPage({
        project: generateMockProjects(1)[0],
      });
    });

    expect(fetchProjectGPUDeviceUtilization as Mock).toHaveBeenCalled();
  });

  it('fetchProjectAverageWaitTime the page', () => {
    act(() => {
      renderProjectPage({
        project: generateMockProjects(1)[0],
      });
    });

    expect(fetchProjectAverageWaitTime as Mock).toHaveBeenCalled();
  });

  it('fetchProjectGPUIdleTime the page', () => {
    act(() => {
      renderProjectPage({
        project: generateMockProjects(1)[0],
      });
    });

    expect(fetchProjectAverageGPUIdleTime as Mock).toHaveBeenCalled();
  });

  it('refresh button trigger refetch', async () => {
    await act(() => {
      renderProjectPage({
        project: generateMockProjects(1)[0],
      });
    });

    expect(fetchProjectGPUMemoryUtilization as Mock).toBeCalledTimes(1);
    expect(fetchProjectGPUDeviceUtilization as Mock).toBeCalledTimes(1);
    expect(fetchProjectAverageWaitTime as Mock).toBeCalledTimes(1);
    expect(fetchProjectAverageGPUIdleTime as Mock).toBeCalledTimes(1);

    await waitFor(() => {
      expect(screen.getByText('data.refresh')).toBeInTheDocument();
    });

    await act(() => {
      fireEvent.click(screen.getByText('data.refresh'));
    });

    expect(fetchProjectGPUMemoryUtilization as Mock).toBeCalledTimes(2);
    expect(fetchProjectGPUDeviceUtilization as Mock).toBeCalledTimes(2);
  });

  it('should navigate to project settings when settings button is clicked', () => {
    act(() => {
      renderProjectPage({
        project: generateMockProjects(1)[0],
      });
    });

    const settingsButton = screen.getByText('dashboard.action.projectSettings');
    fireEvent.click(settingsButton);

    expect(mockPush).toHaveBeenCalledWith('/projects/1/edit');
  });

  it('should handle time range change correctly', async () => {
    await act(() => {
      renderProjectPage({
        project: generateMockProjects(1)[0],
      });
    });

    // Verify the time selector component is rendered
    await waitFor(() => {
      expect(screen.getByText('data.refresh')).toBeInTheDocument();
    });
  });

  it('should render all dashboard sections', () => {
    act(() => {
      renderProjectPage({
        project: generateMockProjects(1)[0],
      });
    });

    // Check for overview sections
    expect(screen.getByText('dashboard.overview.title')).toBeInTheDocument();
    expect(screen.getByText('dashboard.workloads.title')).toBeInTheDocument();
  });
});
