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

import { deleteProject } from '@/services/app/projects';

import { generateMockProjects } from '../../../../__mocks__/utils/project-mock';
import { gigabytesToBytes } from '@/utils/app/memory';

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

vi.mock('@/services/app/projects', () => ({
  deleteProject: vi.fn(),
  fetchSubmittableProjects: vi.fn(() =>
    Promise.resolve({
      projects: [
        { id: 'project1', name: 'Project 1' },
        { id: 'project2', name: 'Project 2' },
      ],
    }),
  ),
}));

describe('ProjectTable', () => {
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
      expect(vi.mocked(deleteProject)).toHaveBeenCalledWith('2');
    });
  });
});
