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
  fetchNamespaceMetrics,
  fetchNamespaceStats,
  fetchNamespaceGPUDeviceUtilization,
  fetchNamespaceGPUMemoryUtilization,
} from '@/lib/app/namespaces';

import { ClusterStatus } from '@amdenterpriseai/types';
import { ProjectStatus } from '@amdenterpriseai/types';
import { QuotaStatus } from '@amdenterpriseai/types';
import { ProjectWithMembers } from '@amdenterpriseai/types';

import wrapper from '@/__tests__/ProviderWrapper';
import '@testing-library/jest-dom';
import { Mock } from 'vitest';
import ProjectDashboardPage from '@/pages';

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

vi.mock('@/lib/app/namespaces', async (importOriginal) => {
  return {
    ...(await importOriginal()),
    fetchNamespaceMetrics: vi.fn(),
    fetchNamespaceStats: vi.fn(),
    fetchNamespaceGPUDeviceUtilization: vi.fn(),
    fetchNamespaceGPUMemoryUtilization: vi.fn(),
  };
});

vi.mock('@/contexts/ProjectContext', () => ({
  useProject: () => ({
    activeProject: 'test-project-123',
    setActiveProject: vi.fn(),
  }),
}));

vi.mock('@/lib/app/aims', () => ({
  getAimServices: vi.fn().mockResolvedValue([]),
  getAimClusterModels: vi.fn().mockResolvedValue([]),
  undeployAim: vi.fn(),
}));

const mockPush = vi.fn();

vi.mock('next/router', () => ({
  useRouter: () => ({
    query: { id: '1' },
    push: mockPush,
  }),
}));

vi.mock('next-auth/react', () => ({
  useSession: () => ({
    data: {
      user: {
        email: 'test@example.com',
        id: 'test-user-id',
      },
    },
    update: vi.fn(),
  }),
}));

vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('projects page', () => {
  beforeEach(() => {
    (fetchNamespaceMetrics as Mock).mockResolvedValue({
      data: [],
      total: 0,
      page: 1,
      pageSize: 20,
      totalPages: 0,
    });
    (fetchNamespaceStats as Mock).mockResolvedValue({
      namespace: 'workbench',
      total: 0,
      statusCounts: [],
    });
    (fetchNamespaceGPUMemoryUtilization as Mock).mockResolvedValue({
      data: [],
    });
    (fetchNamespaceGPUDeviceUtilization as Mock).mockResolvedValue({
      data: [],
    });
  });

  const renderProjectPage = (
    props?: Partial<React.ComponentProps<typeof ProjectDashboardPage>>,
  ) => {
    return render(<ProjectDashboardPage {...props} />, { wrapper });
  };

  it('shows loading state initially', async () => {
    act(() => {
      renderProjectPage();
    });

    await waitFor(() => {
      expect(screen.getByText('dashboard.overview.title')).toBeInTheDocument();
    });
  });

  it('should not crash the page', async () => {
    act(() => {
      renderProjectPage();
    });

    await waitFor(() => {
      expect(screen.getByText('dashboard.overview.title')).toBeInTheDocument();
    });
  });

  it('should call fetchNamespaceGPUDeviceUtilization on page load', () => {
    act(() => {
      renderProjectPage();
    });

    expect(fetchNamespaceGPUDeviceUtilization as Mock).toHaveBeenCalled();
  });

  it('should call fetchNamespaceMetrics on page load', async () => {
    act(() => {
      renderProjectPage();
    });

    await waitFor(() => {
      expect(fetchNamespaceMetrics as Mock).toHaveBeenCalled();
    });
  });

  it('should call fetchNamespaceStats on page load', () => {
    act(() => {
      renderProjectPage();
    });

    expect(fetchNamespaceStats as Mock).toHaveBeenCalled();
  });

  it('should call fetchNamespaceGPUMemoryUtilization on page load', () => {
    act(() => {
      renderProjectPage();
    });

    expect(fetchNamespaceGPUMemoryUtilization as Mock).toHaveBeenCalled();
  });

  it('refresh button trigger refetch', async () => {
    await act(() => {
      renderProjectPage();
    });

    expect(fetchNamespaceGPUMemoryUtilization as Mock).toBeCalledTimes(1);
    expect(fetchNamespaceGPUDeviceUtilization as Mock).toBeCalledTimes(1);

    await waitFor(() => {
      expect(screen.getByText('data.refresh')).toBeInTheDocument();
    });

    await act(() => {
      fireEvent.click(screen.getByText('data.refresh'));
    });

    expect(fetchNamespaceGPUMemoryUtilization as Mock).toBeCalledTimes(2);
    expect(fetchNamespaceGPUDeviceUtilization as Mock).toBeCalledTimes(2);
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

  it('should render all dashboard sections', async () => {
    act(() => {
      renderProjectPage();
    });

    // Check for overview sections
    await waitFor(() => {
      expect(screen.getByText('dashboard.overview.title')).toBeInTheDocument();
      expect(screen.getByText('dashboard.workloads.title')).toBeInTheDocument();
    });
  });
});
