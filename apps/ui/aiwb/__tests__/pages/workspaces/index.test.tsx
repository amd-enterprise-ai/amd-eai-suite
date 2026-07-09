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
import { SessionProvider } from 'next-auth/react';

import {
  mockCatalogItems,
  mockProjectScopedCatalogItems,
} from '@/__mocks__/services/app/catalogs.data';
import {
  getCatalogItems,
  listAllWorkloads,
  deleteWorkspace,
} from '@/lib/app/workloads';

import { generateMockWorkspaceWorkloads } from '@/__mocks__/utils/workloads-mock';

import { WorkloadType } from '@amdenterpriseai/types';
import { WorkloadStatus } from '@/types/enums/workloads';

import WorkspacesPage from '@/pages/[project]/workspaces';

import wrapper from '@/__tests__/ProviderWrapper';
import { Mock, vi } from 'vitest';

vi.mock('@/lib/app/workloads', async (importOriginal) => ({
  ...(await importOriginal()),
  getCatalogItems: vi.fn(),
  listAllWorkloads: vi.fn(),
  deleteWorkspace: vi.fn(),
}));

// Mock RequestSoftware to avoid loading its bg.svg asset in jsdom
vi.mock('@/components/shared/RequestSoftware/RequestSoftware', () => ({
  RequestSoftware: () => <div data-testid="request-software" />,
}));

// Mock next/image: the real component rejects relative srcs and requires a
// configured loader, neither of which exist in jsdom.
vi.mock('next/image', () => ({
  default: ({ src, alt, width, height, className }: any) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={alt}
      width={width}
      height={height}
      className={className}
    />
  ),
}));

const mockSession = {
  error: null as any,
  expires: '2125-01-01T00:00:00',
  user: {
    id: 'test',
    email: 'user@amd.com',
    roles: [],
  },
};

describe('Catalog Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (getCatalogItems as Mock).mockResolvedValue(mockCatalogItems);
    (listAllWorkloads as Mock).mockResolvedValue([]);
  });

  it('renders the catalog page', async () => {
    await act(async () => {
      render(
        <SessionProvider session={mockSession}>
          <WorkspacesPage />
        </SessionProvider>,
        { wrapper },
      );
    });

    await waitFor(() => {
      expect(screen.getByText('Test workload 1')).toBeInTheDocument();
      expect(screen.getByText('Test workload 2')).toBeInTheDocument();
    });
  });

  it.skip('allows filtering catalog items by category', async () => {
    await act(async () => {
      render(
        <SessionProvider session={mockSession}>
          <WorkspacesPage />
        </SessionProvider>,
        { wrapper },
      );
    });

    const filterButton = screen.getByTestId('catalog-category-filter');
    await act(async () => {
      fireEvent.click(filterButton);
    });

    const developmentOption = await screen.findByTestId('development-option');
    await act(async () => {
      fireEvent.click(developmentOption);
    });

    expect(screen.getByText('Test workload 2')).toBeInTheDocument();
    expect(screen.queryByText('Test workload 1')).not.toBeInTheDocument();
  });

  it('allows searching catalog items by text', async () => {
    await act(async () => {
      render(
        <SessionProvider session={mockSession}>
          <WorkspacesPage />
        </SessionProvider>,
        { wrapper },
      );
    });

    const searchInput = screen.getByPlaceholderText(
      'actions.search.placeholder',
    );
    fireEvent.change(searchInput, { target: { value: 'Test workload 2' } });

    await waitFor(() => {
      expect(screen.getByText('Test workload 2')).toBeInTheDocument();
      expect(screen.queryByText('Test workload 1')).not.toBeInTheDocument();
    });
  });

  it('allows refreshing the catalog', async () => {
    await act(async () => {
      render(
        <SessionProvider session={mockSession}>
          <WorkspacesPage />
        </SessionProvider>,
        { wrapper },
      );
    });

    // Wait for the initial query to complete
    await waitFor(() => {
      expect(getCatalogItems).toHaveBeenCalledTimes(1);
    });

    // Reset the mock to clearly track the second call
    vi.clearAllMocks();
    const refreshButton = screen.getByRole('button', { name: /refresh/i });
    await act(async () => {
      fireEvent.click(refreshButton);
    });

    await waitFor(() => {
      expect(getCatalogItems).toHaveBeenCalledTimes(1);
    });
  });

  it('renders the catalog page with user scope without running workloads', async () => {
    (getCatalogItems as Mock).mockResolvedValue([mockCatalogItems[0]]);
    (listAllWorkloads as Mock).mockResolvedValue([]);

    await act(async () => {
      render(
        <SessionProvider session={mockSession}>
          <WorkspacesPage />
        </SessionProvider>,
        { wrapper },
      );
    });

    await waitFor(() => {
      expect(screen.getByText('Test workload 1')).toBeInTheDocument();
      expect(screen.getByText('list.actions.deploy')).toBeInTheDocument();
    });
  });

  it('renders the catalog page with user scope with running workloads', async () => {
    (getCatalogItems as Mock).mockResolvedValue([mockCatalogItems[0]]);

    (listAllWorkloads as Mock).mockResolvedValue(
      generateMockWorkspaceWorkloads(
        1,
        mockCatalogItems[0].name,
        WorkloadStatus.RUNNING,
        WorkloadType.WORKSPACE,
      ),
    );

    await act(async () => {
      render(
        <SessionProvider session={mockSession}>
          <WorkspacesPage />
        </SessionProvider>,
        { wrapper },
      );
    });

    await waitFor(() => {
      expect(screen.getByText('Test workload 1')).toBeInTheDocument();
      expect(screen.queryByText('list.actions.deploy')).not.toBeInTheDocument();
      expect(screen.getByText('list.actions.undeploy')).toBeInTheDocument();
      expect(screen.getByText('list.actions.launch')).toBeInTheDocument();
    });
  });

  it('renders the catalog page with project scope without running workloads', async () => {
    (getCatalogItems as Mock).mockResolvedValue(mockProjectScopedCatalogItems);
    (listAllWorkloads as Mock).mockResolvedValue([]);

    await act(async () => {
      render(
        <SessionProvider session={mockSession}>
          <WorkspacesPage />
        </SessionProvider>,
        { wrapper },
      );
    });

    await waitFor(() => {
      expect(
        screen.getAllByText('MLflow Tracking Server')[0],
      ).toBeInTheDocument();
      expect(screen.getByText('list.actions.deploy')).toBeInTheDocument();
    });
  });

  it('renders the catalog page with project scope with running workloads', async () => {
    (getCatalogItems as Mock).mockResolvedValue(mockProjectScopedCatalogItems);

    (listAllWorkloads as Mock).mockResolvedValue(
      generateMockWorkspaceWorkloads(
        1,
        mockProjectScopedCatalogItems[0].name,
        WorkloadStatus.RUNNING,
        WorkloadType.WORKSPACE,
      ),
    );

    await act(async () => {
      render(
        <SessionProvider session={mockSession}>
          <WorkspacesPage />
        </SessionProvider>,
        { wrapper },
      );
    });

    await waitFor(() => {
      expect(
        screen.getAllByText('MLflow Tracking Server')[0],
      ).toBeInTheDocument();
      expect(screen.queryByText('list.actions.deploy')).not.toBeInTheDocument();
      expect(screen.getByText('list.actions.undeploy')).toBeInTheDocument();
      expect(screen.getByText('list.actions.launch')).toBeInTheDocument();
    });
  });

  it('Workspace page calls listAllWorkloads with type WORKSPACE and status RUNNING, PENDING, FAILED', async () => {
    await act(async () => {
      render(
        <SessionProvider session={mockSession}>
          <WorkspacesPage />
        </SessionProvider>,
        { wrapper },
      );
    });

    expect(listAllWorkloads).toHaveBeenCalledWith('project1', {
      type: [WorkloadType.WORKSPACE],
      status: [
        WorkloadStatus.RUNNING,
        WorkloadStatus.PENDING,
        WorkloadStatus.FAILED,
      ],
    });
  });

  it('displays pending label on catalog item card when workload is pending', async () => {
    (getCatalogItems as Mock).mockResolvedValue([mockCatalogItems[0]]);

    (listAllWorkloads as Mock).mockResolvedValue(
      generateMockWorkspaceWorkloads(
        1,
        mockCatalogItems[0].name,
        WorkloadStatus.PENDING,
        WorkloadType.WORKSPACE,
      ),
    );

    await act(async () => {
      render(
        <SessionProvider session={mockSession}>
          <WorkspacesPage />
        </SessionProvider>,
        { wrapper },
      );
    });

    await waitFor(() => {
      expect(screen.getByText('Test workload 1')).toBeInTheDocument();
      expect(screen.getByText('list.actions.pending')).toBeInTheDocument();
      expect(screen.queryByText('list.actions.launch')).not.toBeInTheDocument();
    });
  });

  it('shows Failed chip and Delete failed workload when a workload has FAILED status', async () => {
    (getCatalogItems as Mock).mockResolvedValue([mockCatalogItems[0]]);

    const failedWorkloadsResponse = generateMockWorkspaceWorkloads(
      1,
      mockCatalogItems[0].name,
      WorkloadStatus.FAILED,
      WorkloadType.WORKSPACE,
    );
    (listAllWorkloads as Mock).mockResolvedValue(failedWorkloadsResponse);

    await act(async () => {
      render(
        <SessionProvider session={mockSession}>
          <WorkspacesPage />
        </SessionProvider>,
        { wrapper },
      );
    });

    await waitFor(() => {
      expect(screen.getByText('Test workload 1')).toBeInTheDocument();
      expect(screen.getByText('status.Failed')).toBeInTheDocument();
      expect(
        screen.getByText('list.actions.deleteFailedWorkload'),
      ).toBeInTheDocument();
      expect(screen.queryByText('list.actions.deploy')).not.toBeInTheDocument();
      expect(
        screen.queryByText('list.actions.undeploy'),
      ).not.toBeInTheDocument();
    });
  });

  it('calls deleteWorkspace with failed workspace id when Delete failed workload is confirmed', async () => {
    (getCatalogItems as Mock).mockResolvedValue([mockCatalogItems[0]]);

    const failedWorkloadsResponse = generateMockWorkspaceWorkloads(
      1,
      mockCatalogItems[0].name,
      WorkloadStatus.FAILED,
      WorkloadType.WORKSPACE,
    );
    const failedWorkloadId = failedWorkloadsResponse[0].id;
    (listAllWorkloads as Mock).mockResolvedValue(failedWorkloadsResponse);
    (deleteWorkspace as Mock).mockResolvedValue(undefined);

    await act(async () => {
      render(
        <SessionProvider session={mockSession}>
          <WorkspacesPage />
        </SessionProvider>,
        { wrapper },
      );
    });

    await waitFor(() => {
      expect(
        screen.getByText('list.actions.deleteFailedWorkload'),
      ).toBeInTheDocument();
    });

    await act(async () => {
      fireEvent.click(screen.getByText('list.actions.deleteFailedWorkload'));
    });

    await waitFor(() => {
      expect(screen.getByText('undeployModal.title')).toBeInTheDocument();
    });

    const confirmButton = screen.getByText('actions.confirm.title');
    await act(async () => {
      fireEvent.click(confirmButton);
    });

    await waitFor(() => {
      expect(deleteWorkspace).toHaveBeenCalledWith(
        'project1',
        failedWorkloadId,
      );
    });
  });
});
