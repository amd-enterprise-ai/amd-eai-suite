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

import { deleteProject, fetchSubmittableProjects } from '@/services/app';
import { useAccessControl } from '@/hooks/useAccessControl';

import { generateMockProjects } from '@/__mocks__/utils/project-mock';
import { gigabytesToBytes } from '@amdenterpriseai/utils/app';

import { ClusterStatus } from '@/types/enums/cluster-status';
import { ProjectTableField } from '@/types/enums/project-table-fields';
import { QuotaResource, QuotaStatus } from '@/types/enums/quotas';
import { ProjectWithResourceAllocation } from '@/types/projects';

import ProjectTable from '@/components/features/projects/ProjectTable';

import wrapper from '@/__tests__/ProviderWrapper';

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
  totalNodes: 2,
  availableNodes: 2,
  gpuInfo: {
    vendor: 'AMD',
    type: '740c',
    name: 'Instinct MI250X',
    memoryBytesPerDevice: gigabytesToBytes(96),
  },
  totalNodeCount: 2,
  availableNodeCount: 2,
  assignedQuotaCount: 1,
  createdAt: '2025-03-11T23:14:03.733668Z',
  gpuAllocationPercentage: 18.75,
  cpuAllocationPercentage: 27.08,
  memoryAllocationPercentage: 20.0,
};

const cluster = {
  id: 'cluster1',
  name: 'Cluster 1',
  status: ClusterStatus.HEALTHY,
  workbenchBaseUrl: 'https://workbench.example.com',
  ...extraClusterInfo,
};

const clusterWithoutWorkbench = {
  id: 'cluster2',
  name: 'Cluster 2',
  status: ClusterStatus.HEALTHY,
  workbenchBaseUrl: undefined,
  ...extraClusterInfo,
};

const mockProject: ProjectWithResourceAllocation = {
  ...generateMockProjects(1)[0],
  cluster: cluster,
  quota: {
    status: QuotaStatus.READY,
    [QuotaResource.GPU]: 8,
    [QuotaResource.CPU]: 2000,
    [QuotaResource.RAM]: gigabytesToBytes(24),
    [QuotaResource.DISK]: gigabytesToBytes(10),
  },
};

const mockProjects: ProjectWithResourceAllocation[] = [
  {
    ...mockProject,
    gpuAllocationPercentage: 100.0,
    cpuAllocationPercentage: 50.0,
    memoryAllocationPercentage: 50.0,
    gpuAllocationExceeded: false,
    cpuAllocationExceeded: false,
    memoryAllocationExceeded: false,
  },
  {
    ...mockProject,
    id: '2',
    gpuAllocationPercentage: 100.0,
    cpuAllocationPercentage: 50.0,
    memoryAllocationPercentage: 50.0,
    gpuAllocationExceeded: false,
    cpuAllocationExceeded: false,
    memoryAllocationExceeded: false,
  },
];

vi.mock('@/services/app', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/services/app')>()),
  deleteProject: vi.fn(),
  fetchSubmittableProjects: vi.fn(() =>
    Promise.resolve({
      projects: [
        { id: 'project1', name: 'Project 1' },
        { id: 'project2', name: 'Project 2' },
      ],
    }),
  ),
  fetchOrganization: vi.fn().mockResolvedValue({ idpLinked: false }),
}));

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

describe('ProjectTable', () => {
  beforeEach(() => {
    vi.mocked(useAccessControl).mockReturnValue(adminAccessControl);
  });

  it('renders correct columns', async () => {
    act(() => {
      render(<ProjectTable projects={mockProjects} />, {
        wrapper,
      });
    });
    const statusColumn = screen.getByText(
      `list.projects.headers.${ProjectTableField.STATUS}.title`,
    );
    const nameColumn = screen.getByText(
      `list.projects.headers.${ProjectTableField.NAME}.title`,
    );
    const gpuAllocationColumn = screen.getByText(
      `list.projects.headers.${ProjectTableField.GPU_ALLOCATION}.title`,
    );
    const cpuAllocationColumn = screen.getByText(
      `list.projects.headers.${ProjectTableField.CPU_ALLOCATION}.title`,
    );

    expect(statusColumn).toBeInTheDocument();
    expect(nameColumn).toBeInTheDocument();
    expect(gpuAllocationColumn).toBeInTheDocument();
    expect(cpuAllocationColumn).toBeInTheDocument();
  });

  it('should call deleteClusterAPI if the delete dropdown is clicked and confirmed', async () => {
    await act(async () => {
      render(<ProjectTable projects={mockProjects} />, {
        wrapper,
      });
    });

    await act(() => {
      const dropDowns = screen.getAllByLabelText('list.actions.label');
      expect(dropDowns).toHaveLength(2);
      // Click the dropdown on project-002
      fireEvent.click(dropDowns[1]);
    });

    await act(() => {
      // Click the delete button
      fireEvent.click(screen.getByText('list.projects.actions.delete.label'));
    });
    await act(() => {
      // Confirm the deletion
      fireEvent.click(screen.getByText('actions.confirm.title'));
    });

    await waitFor(() => {
      expect(vi.mocked(deleteProject)).toHaveBeenCalledWith(
        '2',
        expect.any(Object),
      );
    });
  });

  it('should open workbench URL in new window when viewInAiwb is clicked', async () => {
    const windowOpenSpy = vi
      .spyOn(window, 'open')
      .mockImplementation(() => null);

    await act(async () => {
      render(<ProjectTable projects={mockProjects} />, {
        wrapper,
      });
    });

    await act(() => {
      const dropDowns = screen.getAllByLabelText('list.actions.label');
      fireEvent.click(dropDowns[0]);
    });

    await act(() => {
      fireEvent.click(
        screen.getByText('list.projects.actions.viewInAiwb.label'),
      );
    });

    expect(windowOpenSpy).toHaveBeenCalledWith(
      `${cluster.workbenchBaseUrl}/${mockProjects[0].name}`,
      '_blank',
      'noopener,noreferrer',
    );

    windowOpenSpy.mockRestore();
  });

  it('should strip trailing slashes from workbench URL to avoid double-slash', async () => {
    const windowOpenSpy = vi
      .spyOn(window, 'open')
      .mockImplementation(() => null);
    const clusterWithTrailingSlash = {
      ...cluster,
      workbenchBaseUrl: 'https://workbench.example.com/',
    };
    const projectsWithTrailingSlash: ProjectWithResourceAllocation[] = [
      {
        ...mockProjects[0],
        cluster: clusterWithTrailingSlash,
      },
    ];

    await act(async () => {
      render(<ProjectTable projects={projectsWithTrailingSlash} />, {
        wrapper,
      });
    });

    await act(() => {
      const dropDowns = screen.getAllByLabelText('list.actions.label');
      fireEvent.click(dropDowns[0]);
    });

    await act(() => {
      fireEvent.click(
        screen.getByText('list.projects.actions.viewInAiwb.label'),
      );
    });

    expect(windowOpenSpy).toHaveBeenCalledWith(
      `https://workbench.example.com/${mockProjects[0].name}`,
      '_blank',
      'noopener,noreferrer',
    );

    windowOpenSpy.mockRestore();
  });

  it('should disable viewInAiwb when workbenchBaseUrl is not available', async () => {
    const projectsWithoutWorkbench: ProjectWithResourceAllocation[] = [
      {
        ...mockProjects[0],
        cluster: clusterWithoutWorkbench,
      },
    ];

    await act(async () => {
      render(<ProjectTable projects={projectsWithoutWorkbench} />, {
        wrapper,
      });
    });

    await act(() => {
      const dropDowns = screen.getAllByLabelText('list.actions.label');
      fireEvent.click(dropDowns[0]);
    });

    const viewInAiwbItem = screen.getByText(
      'list.projects.actions.viewInAiwb.label',
    );
    expect(
      viewInAiwbItem.closest('[data-disabled="true"]'),
    ).toBeInTheDocument();
  });

  it('should disable viewInAiwb when workbenchBaseUrl has invalid scheme', async () => {
    const projectsWithInvalidUrl: ProjectWithResourceAllocation[] = [
      {
        ...mockProjects[0],
        cluster: {
          ...cluster,
          workbenchBaseUrl: 'ftp://invalid.example.com',
        },
      },
    ];

    await act(async () => {
      render(<ProjectTable projects={projectsWithInvalidUrl} />, {
        wrapper,
      });
    });

    await act(() => {
      const dropDowns = screen.getAllByLabelText('list.actions.label');
      fireEvent.click(dropDowns[0]);
    });

    const viewInAiwbItem = screen.getByText(
      'list.projects.actions.viewInAiwb.label',
    );
    expect(
      viewInAiwbItem.closest('[data-disabled="true"]'),
    ).toBeInTheDocument();
  });

  it('should render openDetails action in dropdown menu', async () => {
    await act(async () => {
      render(<ProjectTable projects={mockProjects} />, {
        wrapper,
      });
    });

    await act(() => {
      const dropDowns = screen.getAllByLabelText('list.actions.label');
      fireEvent.click(dropDowns[0]);
    });

    expect(
      screen.getByText('list.projects.actions.openDetails.label'),
    ).toBeInTheDocument();
  });
});

describe('ProjectTable - non-admin', () => {
  beforeEach(() => {
    vi.mocked(useAccessControl).mockReturnValue({
      ...adminAccessControl,
      isAdministrator: false,
    });
  });

  it('disables rows for projects the user does not have access to', async () => {
    vi.mocked(fetchSubmittableProjects).mockResolvedValue({
      data: [mockProjects[0]],
    });

    await act(async () => {
      render(<ProjectTable projects={mockProjects} />, { wrapper });
    });

    await waitFor(() => {
      const rows = screen.getAllByRole('row');
      const disabledRows = rows.filter(
        (row) => row.getAttribute('data-disabled') === 'true',
      );
      expect(disabledRows).toHaveLength(1);
    });

    const rows = screen.getAllByRole('row');
    const dataRows = rows.filter((row) => row.getAttribute('data-key'));
    const enabledRow = dataRows.find(
      (row) => row.getAttribute('data-disabled') !== 'true',
    );
    const disabledRow = dataRows.find(
      (row) => row.getAttribute('data-disabled') === 'true',
    );

    expect(enabledRow).toBeDefined();
    expect(disabledRow).toBeDefined();
    expect(enabledRow?.getAttribute('data-key')).toBe(mockProjects[0].id);
    expect(disabledRow?.getAttribute('data-key')).toBe(mockProjects[1].id);
  });
});
