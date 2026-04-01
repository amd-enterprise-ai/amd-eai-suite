// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';

import { useAccessControl } from '@/hooks/useAccessControl';

import { getCluster } from '@/services/app';
import { updateProject } from '@/services/app';

import { fetchProjectSecrets } from '@/services/app';
import { fetchProjectStorages } from '@/services/app';

import { generateMockProjectWithMembers } from '@/__mocks__/utils/project-mock';

import { Cluster } from '@amdenterpriseai/types';
import { ClusterStatus } from '@amdenterpriseai/types';
import { QuotaResource } from '@amdenterpriseai/types';

import ProjectEditPage from '@/pages/projects/[id]/edit';

import wrapper from '@/__tests__/ProviderWrapper';
import '@testing-library/jest-dom';
import { Mock } from 'vitest';

vi.mock('@/services/app', async (importOriginal) => {
  return {
    ...(await importOriginal()),
    updateProject: vi.fn(),
    fetchProjectSecrets: vi.fn(),
    fetchProjectStorages: vi.fn(),
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

vi.mock('next-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
  Trans: ({ children }: { children: React.ReactNode }) => children,
}));

const mockRouterPush = vi.fn();
vi.mock('next/router', () => ({
  useRouter: () => ({
    query: { id: 'cluster-1' },
    push: mockRouterPush,
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

describe('projects/[id]', () => {
  const mockUpdateProject = updateProject as Mock;
  const mockProject = generateMockProjectWithMembers(0, 0);

  const renderProjectEditPage = (
    props?: Partial<React.ComponentProps<typeof ProjectEditPage>>,
  ) => {
    return render(
      <ProjectEditPage
        project={mockProject}
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

    // Test switching back to details tab
    const detailsTab = screen.getByText('tab.details.title');
    fireEvent.click(detailsTab);
    expect(detailsTab).toBeInTheDocument();

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

  it('back button pressed will go to dashboard page', () => {
    const { container } = renderProjectEditPage({ cluster: mockCluster });
    fireEvent.click(screen.getByLabelText('actions.back'));
    expect(mockRouterPush).toHaveBeenCalledWith(`/projects/${mockProject.id}`);
  });
});
