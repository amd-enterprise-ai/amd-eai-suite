// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen, waitFor, within } from '@testing-library/react';
import { vi } from 'vitest';
import { deleteWorkload, listWorkloads } from '@/services/app/workloads';
import { getAims } from '@/services/app/aims';
import WorkloadsPage from '@/pages/workloads';
import wrapper from '@/__tests__/ProviderWrapper';
import { mockWorkloads } from '@/__mocks__/services/app/workloads.data';
import userEvent from '@testing-library/user-event';
import { mockAims } from '@/__mocks__/utils/aims-mock';

vi.mock('next/router', () => ({
  useRouter: vi.fn(() => ({
    push: vi.fn(),
    query: {},
    pathname: '/workloads',
  })),
}));

vi.mock('@/services/app/workloads', () => ({
  listWorkloads: vi.fn(),
  deleteWorkload: vi.fn(),
}));

vi.mock('@/services/app/aims', () => ({
  getAims: vi.fn(),
}));

vi.mock('@/services/app/models', () => ({
  getModels: vi.fn(),
}));

vi.mock('@/hooks/useSystemToast', () => ({
  __esModule: true,
  default: () => ({
    toast: {
      success: vi.fn(),
      error: vi.fn(),
    },
  }),
}));

vi.mock('next-auth', () => ({
  getServerSession: vi.fn(() => ({
    user: { email: 'test@example.com' },
    accessToken: 'test-token',
  })),
}));

vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock('next-i18next/serverSideTranslations', () => ({
  serverSideTranslations: vi.fn(() => Promise.resolve({ _nextI18Next: {} })),
}));

// Mock ProjectContext to provide an active project
vi.mock('@/contexts/ProjectContext', () => ({
  useProject: () => ({
    activeProject: 'test-project-123',
    setActiveProject: vi.fn(),
  }),
}));

describe('Workloads Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (listWorkloads as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockWorkloads,
    );
    (deleteWorkload as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      {},
    );
    (getAims as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockAims,
    );
  });

  it('renders the workloads page', async () => {
    render(<WorkloadsPage />, { wrapper });

    // Wait for the workloads to load
    await waitFor(() => {
      expect(listWorkloads).toHaveBeenCalledTimes(1);
    });

    // Verify that core UI elements are displayed
    expect(
      screen.getByPlaceholderText('list.filters.search.placeholder'),
    ).toBeInTheDocument();
    expect(screen.getByText('list.filters.type.label')).toBeInTheDocument();
    expect(screen.getByText('list.filters.status.label')).toBeInTheDocument();
  });

  it('filters workloads by type', async () => {
    render(<WorkloadsPage />, { wrapper });

    // Wait for the workloads to load
    await waitFor(() => {
      expect(listWorkloads).toHaveBeenCalledTimes(1);
    });

    // Check if the type filter button exists
    expect(screen.getByText('list.filters.type.label')).toBeInTheDocument();
  });

  it('renders status filter', async () => {
    render(<WorkloadsPage />, { wrapper });

    // Wait for the workloads to load
    await waitFor(() => {
      expect(listWorkloads).toHaveBeenCalledTimes(1);
    });

    // Check if the status filter button exists
    expect(screen.getByText('list.filters.status.label')).toBeInTheDocument();
  });

  it('renders clear filters button', async () => {
    render(<WorkloadsPage />, { wrapper });

    // Wait for the workloads to load
    await waitFor(() => {
      expect(listWorkloads).toHaveBeenCalledTimes(1);
    });

    const clearButton = screen.getByText('actions.clearFilters.title');

    // Check if clear filters button exists
    expect(clearButton).toBeInTheDocument();
  });

  it('renders refresh button', async () => {
    render(<WorkloadsPage />, { wrapper });

    // Wait for the workloads to load
    await waitFor(() => {
      expect(listWorkloads).toHaveBeenCalledTimes(1);
    });

    const refreshButton = screen.getByRole('button', { name: /refresh/i });

    // Check if refresh button exists
    expect(refreshButton).toBeInTheDocument();
  });

  it('calls listWorkloads on initial render', async () => {
    render(<WorkloadsPage />, { wrapper });

    // Verify the API was called once
    await waitFor(() => {
      expect(listWorkloads).toHaveBeenCalledTimes(1);
    });
  });

  it('displays created-by column in the table', async () => {
    render(<WorkloadsPage />, { wrapper });

    // Wait for the workloads to load
    await waitFor(() => {
      expect(listWorkloads).toHaveBeenCalledTimes(1);
    });

    // Verify that created-by values are displayed in the table
    await waitFor(() => {
      // Check that created-by values from the mock data are displayed
      const testUserElements = screen.getAllByText('test-user');
      expect(testUserElements.length).toBeGreaterThan(0);

      const user2Elements = screen.getAllByText('user-2');
      expect(user2Elements.length).toBeGreaterThan(0);

      const user3Elements = screen.getAllByText('user-3');
      expect(user3Elements.length).toBeGreaterThan(0);
    });
  });

  it('correctly sets isDisabled for openWorkspace action based on workload status', async () => {
    render(<WorkloadsPage />, { wrapper });

    // Wait for the workloads to load and render in the table
    await waitFor(() => {
      expect(listWorkloads).toHaveBeenCalledTimes(1);
      expect(screen.getByText('Jupyter Workspace')).toBeInTheDocument();
    });

    // Find workload-3 (Jupyter Workspace) - status: RUNNING
    const runningWorkspaceRow = screen
      .getByText('Jupyter Workspace')
      .closest('tr');
    expect(runningWorkspaceRow).toBeInTheDocument();

    // Find action button for RUNNING workspace
    const runningActionButton = within(runningWorkspaceRow!).getByRole(
      'button',
      {
        name: /list\.actions\.label/i,
      },
    );
    runningActionButton.click();

    // Wait for menu and check openWorkspace action is NOT disabled
    await waitFor(() => {
      const openWorkspaceAction = screen.getByText(
        'list.actions.openWorkspace.label',
      );
      expect(openWorkspaceAction).toBeInTheDocument();

      // The action should be enabled (not have aria-disabled="true")
      const menuItem = openWorkspaceAction.closest('[role="menuitem"]');
      expect(menuItem).not.toHaveAttribute('aria-disabled', 'true');
    });

    // Close the menu by clicking outside or pressing Escape
    await userEvent.keyboard('{Escape}');

    // Wait for the menu to close - check that the menu itself is gone
    await waitFor(() => {
      const menuItems = screen.queryAllByRole('menuitem');
      expect(menuItems.length).toBe(0);
    });

    // Find workload-7 (Production Workspace) - status: DELETING
    const deletingWorkspaceRow = screen
      .getByText('Production Workspace')
      .closest('tr');
    expect(deletingWorkspaceRow).toBeInTheDocument();

    // Find action button for DELETING workspace
    const deletingActionButton = within(deletingWorkspaceRow!).getByRole(
      'button',
      {
        name: /list\.actions\.label/i,
      },
    );
    deletingActionButton.click();

    // Wait for menu and check openWorkspace action IS disabled
    await waitFor(() => {
      const openWorkspaceAction = screen.getByText(
        'list.actions.openWorkspace.label',
      );
      expect(openWorkspaceAction).toBeInTheDocument();

      // The action should be disabled (have aria-disabled="true")
      const menuItem = openWorkspaceAction.closest('[role="menuitem"]');
      expect(menuItem).toHaveAttribute('aria-disabled', 'true');
    });
    // Verify that the workloads list API was called with the workloads
    expect(listWorkloads).toHaveBeenCalled();

    // Check that the table/grid is rendered
    const table = screen.queryByRole('grid') || screen.queryByRole('table');
    if (table) {
      expect(table).toBeInTheDocument();
    }
  });
});
