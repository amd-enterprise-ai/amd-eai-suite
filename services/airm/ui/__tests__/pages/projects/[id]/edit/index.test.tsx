// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, fireEvent, render, screen } from '@testing-library/react';

import { useAccessControl } from '@/hooks/useAccessControl';

import { getCluster } from '@/services/app/clusters';
import { updateProject } from '@/services/app/projects';

import { fetchProjectSecrets } from '@/services/app/secrets';
import { fetchProjectStorages } from '@/services/app/storages';

import { generateMockProjectWithMembers } from '@/__mocks__/utils/project-mock';

import { Cluster } from '@/types/clusters';
import { ClusterStatus } from '@/types/enums/cluster-status';
import { QuotaResource } from '@/types/enums/quotas';

import ProjectEditPage from '@/pages/projects/[id]/edit';

import wrapper from '@/__tests__/ProviderWrapper';
import '@testing-library/jest-dom';
import { Mock } from 'vitest';

vi.mock('@/services/app/projects', async (importOriginal) => {
  return {
    ...(await importOriginal()),
    updateProject: vi.fn(),
  };
});

vi.mock('@/services/app/secrets', async (importOriginal) => {
  return {
    ...(await importOriginal()),
    fetchProjectSecrets: vi.fn(),
  };
});

vi.mock('@/services/app/storages', async (importOriginal) => {
  return {
    ...(await importOriginal()),
    fetchProjectStorages: vi.fn(),
  };
});

vi.mock('@/services/app/clusters', async (importOriginal) => {
  return {
    ...(await importOriginal()),
    getCluster: vi.fn(),
  };
});

vi.mock('@/hooks/useAccessControl', () => ({
  useAccessControl: vi.fn(() => ({
    isRoleManagementEnabled: true,
    isInviteEnabled: true,
    isAdministrator: true,
  })),
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

const mockCluster: Cluster = {
  id: 'cluster-1',
  name: 'Cluster 1',
  status: ClusterStatus.HEALTHY,
  lastHeartbeatAt: new Date().toISOString(),
  availableResources: {
    [QuotaResource.CPU]: 8000,
    [QuotaResource.RAM]: 16000,
    [QuotaResource.DISK]: 100000,
    [QuotaResource.GPU]: 4,
  },
  allocatedResources: {
    [QuotaResource.CPU]: 4000,
    [QuotaResource.RAM]: 8000,
    [QuotaResource.DISK]: 50000,
    [QuotaResource.GPU]: 2,
  },
  totalNodeCount: 2,
  availableNodeCount: 1,
  assignedQuotaCount: 1,
  createdAt: new Date().toISOString(),
  gpuAllocationPercentage: 50.0,
  cpuAllocationPercentage: 50.0,
  memoryAllocationPercentage: 50.0,
};

vi.mock('next/router', () => ({
  useRouter: () => ({
    query: { id: 'cluster-1' },
    push: vi.fn(),
  }),
}));

describe('projects/[id]', () => {
  const mockUpdateProject = updateProject as Mock;

  const renderProjectEditPage = (
    props?: Partial<React.ComponentProps<typeof ProjectEditPage>>,
  ) => {
    return render(
      <ProjectEditPage
        project={generateMockProjectWithMembers(0, 0)}
        cluster={props?.cluster ?? mockCluster}
        projectSecrets={props?.projectSecrets ?? []}
        projectStorages={props?.projectStorages ?? []}
        secrets={props?.secrets ?? []}
        storages={props?.storages ?? []}
        {...props}
      />,
      { wrapper },
    );
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should not crash the page', () => {
    const { container } = renderProjectEditPage({ cluster: mockCluster });
    expect(container).toBeTruthy();
  });

  it('should call getCluster on page load with current cluster id', () => {
    renderProjectEditPage({ cluster: mockCluster });
    expect(getCluster).toHaveBeenCalledWith(mockCluster.id);
  });

  it('should show users tab when access management is enabled', () => {
    act(() => {
      renderProjectEditPage();
    });

    expect(screen.getByText('tab.users.title')).toBeInTheDocument();
  });

  it('should show users tab but hide invited users when invite is disabled but access management is enabled', () => {
    // Mock useAccessControl to return enabled access management but disabled invite
    const mockedUseAccessControl = useAccessControl as Mock;
    mockedUseAccessControl.mockReturnValue({
      isAccessManagementEnabled: true,
      isInviteEnabled: false,
      isAdministrator: true,
    });

    act(() => {
      renderProjectEditPage();
    });

    expect(screen.getByText('tab.users.title')).toBeInTheDocument();

    // Reset mock for other tests
    mockedUseAccessControl.mockReturnValue({
      isAccessManagementEnabled: true,
      isInviteEnabled: true,
      isAdministrator: true,
    });
  });

  it('should switch between tabs correctly', () => {
    act(() => {
      renderProjectEditPage({ cluster: mockCluster });
    });

    // Test switching to secrets tab
    const secretsTab = screen.getByText('tab.secrets.title');
    fireEvent.click(secretsTab);
    expect(secretsTab).toBeInTheDocument();

    // Test switching to storages tab
    const storagesTab = screen.getByText('tab.storages.title');
    fireEvent.click(storagesTab);
    expect(storagesTab).toBeInTheDocument();

    // Test switching to users tab
    const usersTab = screen.getByText('tab.users.title');
    fireEvent.click(usersTab);
    expect(usersTab).toBeInTheDocument();

    expect(
      screen.getByText('settings.membersAndInvitedUsers.members.title'),
    ).toBeInTheDocument();

    // Test switching back to quota tab
    const quotaTab = screen.getByText('tab.quota.title');
    fireEvent.click(quotaTab);
    expect(quotaTab).toBeInTheDocument();

    // Test switching back to general tab
    const generalTab = screen.getByText('tab.general.title');
    fireEvent.click(generalTab);
    expect(generalTab).toBeInTheDocument();

    expect(
      screen.getByText('settings.form.deleteProject.title'),
    ).toBeInTheDocument();
  });

  it('fetchProjectSecrets the page', () => {
    act(() => {
      renderProjectEditPage();
    });
    fireEvent.click(screen.getByText('tab.secrets.title'));
    expect(fetchProjectSecrets as Mock).toHaveBeenCalled();
  });

  it('fetchProjectStorages the page', () => {
    act(() => {
      renderProjectEditPage();
    });

    fireEvent.click(screen.getByText('tab.storages.title'));

    expect(fetchProjectStorages as Mock).toHaveBeenCalled();
  });
});
