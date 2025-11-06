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
import { getCatalogItems } from '@/services/app/catalog';
import { listWorkloads } from '@/services/app/workloads';

import { generateMockWorkspaceWorkloads } from '@/__mocks__/utils/workloads-mock';

import { WorkloadStatus, WorkloadType } from '@/types/enums/workloads';

import WorkspacesPage from '@/pages/workspaces';

import wrapper from '@/__tests__/ProviderWrapper';
import { Mock, vi } from 'vitest';

vi.mock('@/services/app/catalog', () => ({
  getCatalogItems: vi.fn(),
}));

vi.mock('@/services/app/workloads', async () => {
  const actual = await vi.importActual<
    typeof import('@/services/app/workloads')
  >('@/services/app/workloads');
  return {
    ...actual,
    listWorkloads: vi.fn(),
  };
});

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
    (listWorkloads as Mock).mockResolvedValue([]);
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

  it('allows displaying the items as a list', async () => {
    await act(async () => {
      render(
        <SessionProvider session={mockSession}>
          <WorkspacesPage />
        </SessionProvider>,
        { wrapper },
      );
    });

    const listButton = screen.getByTestId('display-option-list');
    await act(async () => {
      fireEvent.click(listButton);
    });

    expect(screen.getByRole('grid')).toBeInTheDocument();
    expect(screen.getByText('Test workload 1')).toBeInTheDocument();
    expect(screen.getByText('Test workload 2')).toBeInTheDocument();
  });

  it('renders the catalog page with user scope without running workloads', async () => {
    (getCatalogItems as Mock).mockResolvedValue([mockCatalogItems[0]]);

    (listWorkloads as Mock).mockResolvedValue([]);

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

    (listWorkloads as Mock).mockResolvedValue(
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

    (listWorkloads as Mock).mockResolvedValue([]);

    await act(async () => {
      render(
        <SessionProvider session={mockSession}>
          <WorkspacesPage />
        </SessionProvider>,
        { wrapper },
      );
    });

    await waitFor(() => {
      expect(screen.getByText('MLflow Tracking Server')).toBeInTheDocument();
      expect(screen.getByText('list.actions.deploy')).toBeInTheDocument();
    });
  });

  it('renders the catalog page with project scope with running workloads', async () => {
    (getCatalogItems as Mock).mockResolvedValue(mockProjectScopedCatalogItems);

    (listWorkloads as Mock).mockResolvedValue(
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
      expect(screen.getByText('MLflow Tracking Server')).toBeInTheDocument();
      expect(screen.queryByText('list.actions.deploy')).not.toBeInTheDocument();
      expect(screen.getByText('list.actions.undeploy')).toBeInTheDocument();
      expect(screen.getByText('list.actions.launch')).toBeInTheDocument();
    });
  });

  it('Workspace page calls correct filter of type WORKSPACE and status PENDING, RUNNING', async () => {
    await act(async () => {
      render(
        <SessionProvider session={mockSession}>
          <WorkspacesPage />
        </SessionProvider>,
        { wrapper },
      );
    });

    expect(listWorkloads).toHaveBeenCalledWith('project1', {
      withResources: true,
      type: [WorkloadType.WORKSPACE],
      status: [WorkloadStatus.RUNNING, WorkloadStatus.PENDING],
    });
  });
});
