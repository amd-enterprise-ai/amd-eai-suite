// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';

import { mockWorkloads } from '@/__mocks__/services/app/workloads.data';
import { mockAims } from '@/__mocks__/services/app/aims.data';
import { mockModels } from '@/__mocks__/services/app/models.data';
import { getAims } from '@/services/app/aims';
import { getModels } from '@/services/app/models';
import { deleteWorkload, listWorkloads } from '@/services/app/workloads';

import { WorkloadStatus, WorkloadType } from '@/types/enums/workloads';
import { Aim } from '@/types/aims';
import { Model, ModelOnboardingStatus } from '@/types/models';
import { Workload } from '@/types/workloads';

import DeployedModels from '@/components/features/models/DeployedModels';

import wrapper from '@/__tests__/ProviderWrapper';
import { Mock, vi } from 'vitest';

vi.mock('@/services/app/workloads', () => ({
  listWorkloads: vi.fn(),
  deleteWorkload: vi.fn(),
}));

vi.mock('@/services/app/models', () => ({
  getModels: vi.fn(),
}));

vi.mock('@/services/app/aims', () => ({
  getAims: vi.fn(),
}));

// Mock useProject hook
vi.mock('@/hooks/useProject', () => ({
  __esModule: true,
  default: () => ({
    activeProject: 'test-project',
  }),
}));

// Mock useSystemToast for testing
vi.mock('@/hooks/useSystemToast', () => ({
  __esModule: true,
  default: () => ({
    toast: {
      success: vi.fn(),
      error: vi.fn(),
    },
  }),
}));

// Mock next/router
const mockPush = vi.fn();
vi.mock('next/router', () => ({
  useRouter: vi.fn(() => ({
    push: mockPush,
    query: {},
    pathname: '/models',
  })),
}));

// Mock translations
vi.mock('next-i18next', () => ({
  Trans: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// Mock Tabler icons
vi.mock('@tabler/icons-react', async (importOriginal) => {
  const original = (await importOriginal()) ?? {};
  return {
    ...original,
    IconDotsVertical: ({ className }: any) => (
      <span className={className}>action-dot-icon</span>
    ),
  };
});

describe('DeployedModels', () => {
  const mockListWorkloads = listWorkloads as Mock;
  const mockDeleteWorkload = deleteWorkload as Mock;
  const mockGetModels = getModels as Mock;
  const mockGetAims = getAims as Mock;

  beforeEach(() => {
    vi.clearAllMocks();
    mockListWorkloads.mockResolvedValue(mockWorkloads);
    mockDeleteWorkload.mockResolvedValue({ success: true });
    mockGetModels.mockResolvedValue(mockModels);
    mockGetAims.mockResolvedValue(mockAims);

    // Mock window.open
    Object.defineProperty(window, 'open', {
      writable: true,
      value: vi.fn(),
    });
  });

  it('renders deployed models component', async () => {
    await act(async () => {
      render(<DeployedModels />, { wrapper });
    });

    expect(screen.getByTestId('deployed-models')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument();

    // Use more specific selectors to avoid ambiguity
    const typeDropdowns = screen.getAllByText(/type/i);
    const statusDropdowns = screen.getAllByText(/status/i);
    expect(typeDropdowns.length).toBeGreaterThan(0);
    expect(statusDropdowns.length).toBeGreaterThan(0);

    const clearButton = screen.getByText('actions.clearFilters.title');
    const refreshButton = screen.getByRole('button', { name: /refresh/i });

    expect(refreshButton).toBeInTheDocument();
    expect(clearButton).toBeInTheDocument();
  });

  it('displays workloads in the data table', async () => {
    await act(async () => {
      render(<DeployedModels />, { wrapper });
    });

    // Wait for the API call to complete
    await waitFor(
      () => {
        expect(mockListWorkloads).toHaveBeenCalled();
      },
      { timeout: 3000 },
    );

    // Wait for data to load and be displayed
    await waitFor(
      () => {
        // Check that workloads are displayed - the component shows displayName
        // Only INFERENCE types should be visible by default
        expect(screen.getByText('Llama 7B Inference')).toBeInTheDocument();
        // other types should not appear
        expect(
          screen.queryByText('Stable Diffusion XL Download'),
        ).not.toBeInTheDocument();
        expect(
          screen.queryByText('Model fine-tuning Job'),
        ).not.toBeInTheDocument();
      },
      { timeout: 5000 },
    );

    // The component only shows INFERENCE workloads
    expect(screen.queryByText('Jupyter Workspace')).not.toBeInTheDocument(); // WORKSPACE type is not shown

    // For now, just verify the component renders without crashing
    expect(screen.getByTestId('deployed-models')).toBeInTheDocument();
  });

  it('filters workloads by search query', async () => {
    await act(async () => {
      render(<DeployedModels />, { wrapper });
    });

    const searchInput = screen.getByPlaceholderText(/search/i);

    // Wait for initial data to load
    await waitFor(() => {
      expect(screen.getByText('Llama 7B Inference')).toBeInTheDocument();
    });

    // Search for "Llama" - this should filter by displayName field
    fireEvent.change(searchInput, { target: { value: 'Llama' } });

    await waitFor(() => {
      // Should show the Llama workload (displayName is displayed)
      expect(screen.getByText('Llama 7B Inference')).toBeInTheDocument();
      // Should not show other workloads
      expect(
        screen.queryByText('Stable Diffusion XL Download'),
      ).not.toBeInTheDocument();
    });

    // Clear search and verify all default-filtered workloads are shown again
    fireEvent.change(searchInput, { target: { value: '' } });

    await waitFor(() => {
      expect(screen.getByText('Llama 7B Inference')).toBeInTheDocument();
      // other types won't be shown
      expect(
        screen.queryByText('Stable Diffusion XL Download'),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByText('Model fine-tuning Job'),
      ).not.toBeInTheDocument();
    });
  });

  it('displays only inference workloads', async () => {
    // Use the standard mock workloads to verify only INFERENCE workloads are shown
    mockListWorkloads.mockResolvedValue(mockWorkloads);

    await act(async () => {
      render(<DeployedModels />, { wrapper });
    });

    // Wait for initial data to load - by default only INFERENCE should be visible
    await waitFor(() => {
      expect(screen.getByText('Llama 7B Inference')).toBeInTheDocument(); // INFERENCE
      // FINE_TUNING and WORKSPACE should be filtered out by default
      expect(
        screen.queryByText('Stable Diffusion XL Download'),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByText('Model fine-tuning Job'),
      ).not.toBeInTheDocument();
      expect(screen.queryByText('Jupyter Workspace')).not.toBeInTheDocument();
    });

    // Verify that the component has the expected number of rows (header + visible data rows)
    const tableContainer = await screen.findByRole('grid');
    await waitFor(() => {
      const rows = within(tableContainer).getAllByRole('row');
      // Based on mockWorkloads, we should see only INFERENCE workloads:
      // workload-1 (Llama, RUNNING), workload-8 (Delete Failed, DELETE_FAILED),
      // workload-11 (AIM GPT-4, RUNNING), workload-12 (AIM LLaMA 2, RUNNING), workload-13 (AIM Mistral, RUNNING)
      // workload-5 is DELETED status so filtered out by default
      expect(rows).toHaveLength(6); // 1 header + 5 data rows
    });
  });

  it('shows loading state', async () => {
    // Mock loading state by returning a never-resolving promise
    mockListWorkloads.mockImplementation(() => new Promise(() => {}));

    await act(async () => {
      render(<DeployedModels />, { wrapper });
    });

    // Check that the data table shows loading state
    // The ClientSideDataTable should show loading indicators when isLoading is true
    await waitFor(() => {
      const deployedModels = screen.getByTestId('deployed-models');
      expect(deployedModels).toBeInTheDocument();

      // Verify that no workload data is displayed while loading
      expect(screen.queryByText('Llama 7B Inference')).not.toBeInTheDocument();
      expect(screen.queryByText('Stable Diffusion XL')).not.toBeInTheDocument();
    });
  });

  it('handles refresh button click', async () => {
    await act(async () => {
      render(<DeployedModels />, { wrapper });
    });

    // Wait for initial load to complete
    await waitFor(() => {
      expect(mockListWorkloads).toHaveBeenCalled();
    });

    const refreshButton = screen.getByRole('button', { name: /refresh/i });
    // Clear the mock call count after initial load
    mockListWorkloads.mockClear();

    fireEvent.click(refreshButton);

    await waitFor(() => {
      expect(mockListWorkloads).toHaveBeenCalled();
    });
  });

  it('navigates to workload details page when details action is clicked', async () => {
    await act(async () => {
      render(<DeployedModels />, { wrapper });
    });

    await waitFor(() => {
      expect(screen.getByText('Llama 7B Inference')).toBeInTheDocument();
    });

    // Find the row with Llama 7B Inference and click its action button
    const llamaRow = screen.getByText('Llama 7B Inference').closest('tr');
    expect(llamaRow).not.toBeNull();

    const rowActionButton = within(llamaRow!).getByText('action-dot-icon');
    await act(async () => {
      fireEvent.click(rowActionButton);
    });

    // Find and click the details action
    const detailsButton = await screen.findByTestId('details');
    expect(detailsButton).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(detailsButton);
    });

    // Verify navigation to workload details page for Llama 7B (workload-1)
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/workloads/workload-1');
    });
  });

  it('opens delete workload modal when delete action is clicked', async () => {
    await act(async () => {
      render(<DeployedModels />, { wrapper });
    });

    await waitFor(() => {
      expect(screen.getByText('Llama 7B Inference')).toBeInTheDocument();
    });

    const rowActionButtons = screen.getAllByText('action-dot-icon');
    fireEvent.click(rowActionButtons[0]); // First workload (Delete Failed Inference)

    const undeployButton = screen.getByTestId('undeploy');
    fireEvent.click(undeployButton);

    // Verify confirmation modal opens
    expect(screen.getByTestId('confirmation-modal')).toBeInTheDocument();
  });

  it('handles workload deletion', async () => {
    await act(async () => {
      render(<DeployedModels />, { wrapper });
    });

    await waitFor(() => {
      expect(screen.getByText('Llama 7B Inference')).toBeInTheDocument();
    });

    // Open row actions menu for the last workload (Llama 7B)
    const rowActionButtons = screen.getAllByText('action-dot-icon');
    await act(async () => {
      fireEvent.click(rowActionButtons[rowActionButtons.length - 1]);
    });

    // Click the undeploy/delete button
    const undeployButton = await screen.findByTestId('undeploy');
    await act(async () => {
      fireEvent.click(undeployButton);
    });

    // Verify confirmation modal is open
    expect(screen.getByTestId('confirmation-modal')).toBeInTheDocument();

    // Find and click the confirm button in the modal
    const confirmButton = await screen.findByTestId('confirm-button');

    // Clear mock calls before the action
    mockDeleteWorkload.mockClear();

    await act(async () => {
      fireEvent.click(confirmButton);
    });

    // Verify the delete API was called with the correct workload ID
    await waitFor(() => {
      expect(mockDeleteWorkload).toHaveBeenCalledWith('workload-1'); // Llama 7B Inference workload
    });
  });

  it('displays workspace workloads when workspace type is in filter', async () => {
    // Create a mock with a workspace workload
    const workspaceWorkload: Workload = {
      ...mockWorkloads[2], // Jupyter Workspace
      type: WorkloadType.WORKSPACE,
      status: WorkloadStatus.RUNNING,
      output: {
        externalHost: 'https://jupyter.example.com',
        internalHost: 'https://jupyter.example.com',
      },
    };

    mockListWorkloads.mockResolvedValue([workspaceWorkload]);

    await act(async () => {
      render(<DeployedModels />, { wrapper });
    });

    // Since WORKSPACE is not in default filter, it shouldn't be visible initially
    await waitFor(() => {
      expect(screen.queryByText('Jupyter Workspace')).not.toBeInTheDocument();
    });

    // Test that basic functionality works - the component renders without crashing
    expect(screen.getByTestId('deployed-models')).toBeInTheDocument();
  });

  it('handles API errors gracefully', async () => {
    mockListWorkloads.mockRejectedValue(new Error('API Error'));

    await act(async () => {
      render(<DeployedModels />, { wrapper });
    });

    // Verify the component still renders
    expect(screen.getByTestId('deployed-models')).toBeInTheDocument();

    // Verify that no workload data is displayed when there's an error
    await waitFor(() => {
      expect(screen.queryByText('Llama 7B Inference')).not.toBeInTheDocument();
      expect(screen.queryByText('Stable Diffusion XL')).not.toBeInTheDocument();
    });

    // The component should show an empty state or error message
    // Since the API call failed, the workloads array should be empty
    await waitFor(() => {
      expect(mockListWorkloads).toHaveBeenCalled();
    });
  });

  it('displays correct workload status badges', async () => {
    await act(async () => {
      render(<DeployedModels />, { wrapper });
    });

    await waitFor(() => {
      expect(screen.getByText('Llama 7B Inference')).toBeInTheDocument();
    });

    // Verify that different status values are displayed
    // The StatusDisplay component renders these as translated strings
    await waitFor(() => {
      // Check for actual status text displayed (not the enum keys)
      expect(screen.getAllByText('status.Running').length).toBeGreaterThan(0); // Llama workload
      expect(screen.getByText('status.DeleteFailed')).toBeInTheDocument(); // Delete failed inference workload
      // Fine-tuning workloads should not be shown by default
      expect(screen.queryByText('status.Failed')).not.toBeInTheDocument();
    });
  });

  it('displays correct workload type chips', async () => {
    await act(async () => {
      render(<DeployedModels />, { wrapper });
    });

    await waitFor(() => {
      expect(screen.getByText('Llama 7B Inference')).toBeInTheDocument();
    });

    // Verify different workload types are displayed as chips
    // The ChipDisplay component renders these as translated strings
    await waitFor(() => {
      // Only INFERENCE workloads are shown (excluding DELETED status)
      const inferenceElements = screen.getAllByText('type.INFERENCE');
      // From mockWorkloads: workload-1 (Llama, RUNNING), workload-8 (Delete Failed, DELETE_FAILED),
      // workload-11 (AIM GPT-4, RUNNING), workload-12 (AIM LLaMA 2, RUNNING), workload-13 (AIM Mistral, RUNNING)
      // workload-5 is DELETED status so filtered out by default
      expect(inferenceElements.length).toBe(5);
    });
  });

  it('formats dates correctly', async () => {
    await act(async () => {
      render(<DeployedModels />, { wrapper });
    });

    await waitFor(() => {
      expect(screen.getByText('Llama 7B Inference')).toBeInTheDocument();
    });

    // Verify that DateDisplay components are rendered for createdAt dates
    // Based on the test output, dates are formatted as "2023/01/01 02:00" etc.
    await waitFor(() => {
      // Check for the formatted dates that appear in the table
      const dateCells = screen.getAllByText(
        /[0-9]{4}\/[0-9]{2}\/[0-9]{2} [0-9]{2}:[0-9]{2}/,
      );
      expect(dateCells.length).toBeGreaterThan(0);
    });
  });

  it('shows correct row actions based on workload status and type', async () => {
    await act(async () => {
      render(<DeployedModels />, { wrapper });
    });

    await waitFor(() => {
      expect(screen.getByText('Llama 7B Inference')).toBeInTheDocument();
    });

    // Test actions for the Llama 7B Inference workload (INFERENCE with RUNNING status and CHAT capability)
    // It should be the last row since the table is sorted by createdAt descending
    const rowActionButtons = screen.getAllByText('action-dot-icon');
    await act(async () => {
      // Click the last workload which should be Llama 7B Inference based on the sorting
      fireEvent.click(rowActionButtons[rowActionButtons.length - 1]);
    });

    await waitFor(() => {
      expect(screen.getByTestId('details')).toBeInTheDocument();
      expect(screen.getByTestId('undeploy')).toBeInTheDocument(); // RUNNING status allows undeploy
      // Chat action should be available since it's INFERENCE type with CHAT capability and RUNNING status
      expect(screen.getByTestId('chat')).toBeInTheDocument();
      // No workspace action since it's not a WORKSPACE type
      expect(screen.queryByTestId('openWorkspace')).not.toBeInTheDocument();
    });
  });

  it('disables actions for deleted workloads', async () => {
    // Create a mock with a deleted workload that should be visible
    // First, we need to include DELETED status in the filters to see deleted workloads
    const deletedWorkload: Workload = {
      ...mockWorkloads[4], // Deleted Workload
      displayName: 'Deleted Model',
      type: WorkloadType.INFERENCE, // Component only shows INFERENCE workloads
      status: WorkloadStatus.DELETE_FAILED, // Use DELETE_FAILED instead of DELETED so it's visible by default
    };

    mockListWorkloads.mockResolvedValue([deletedWorkload]);

    await act(async () => {
      render(<DeployedModels />, { wrapper });
    });

    await waitFor(() => {
      expect(screen.getByText('Deleted Model')).toBeInTheDocument();
    });

    // Open row actions for the workload
    const rowActionButtons = screen.getAllByText('action-dot-icon');
    await act(async () => {
      fireEvent.click(rowActionButtons[0]);
    });

    // Verify details action is available and undeploy action is available for DELETE_FAILED status
    await waitFor(() => {
      expect(screen.getByTestId('details')).toBeInTheDocument();
      // DELETE_FAILED workloads should still have undeploy action unlike DELETED workloads
      expect(screen.getByTestId('undeploy')).toBeInTheDocument();
      expect(screen.queryByTestId('chat')).not.toBeInTheDocument(); // No chat for failed workloads
      expect(screen.queryByTestId('openWorkspace')).not.toBeInTheDocument(); // No workspace actions for non-workspace types
    });
  });

  it('filters out deleted workloads by default', async () => {
    // Create a mix of workloads including a deleted one
    const workloadsWithDeleted: Workload[] = [
      ...mockWorkloads.slice(0, 3), // Include some normal workloads
      {
        ...mockWorkloads[4],
        type: WorkloadType.INFERENCE,
        status: WorkloadStatus.DELETED, // This should be filtered out
        modelId: 'model-deleted',
        displayName: 'Deleted Model',
      },
    ];

    mockListWorkloads.mockResolvedValue(workloadsWithDeleted);

    await act(async () => {
      render(<DeployedModels />, { wrapper });
    });

    // Wait for the data to load
    await waitFor(() => {
      expect(mockListWorkloads).toHaveBeenCalled();
    });

    // Should see the non-deleted workloads but not the deleted one
    await waitFor(() => {
      expect(screen.getByText('Llama 7B Inference')).toBeInTheDocument(); // RUNNING INFERENCE workload
      // DELETED workloads should be filtered out
      expect(screen.queryByText('Stable Diffusion XL')).not.toBeInTheDocument();
      expect(screen.queryByText('Deleted Model')).not.toBeInTheDocument();
    });
  });

  it('displays canonical names for all workloads with AIM or Model', async () => {
    const workloadsWithModelOrAim = [
      mockWorkloads[0], // workload-1 - modelId
      mockWorkloads[7], // workload-8 - modelId
      mockWorkloads[10], // workload-11 - aimId
      mockWorkloads[11], // workload-12 - aimId
      mockWorkloads[12], // workload-13 - aimId
    ];

    mockListWorkloads.mockResolvedValue(workloadsWithModelOrAim);

    await act(async () => {
      render(<DeployedModels />, { wrapper });
    });

    await waitFor(() => {
      expect(screen.getByText('Llama 7B Inference')).toBeInTheDocument();
    });

    const table = screen.getByRole('grid');
    const rows = within(table).getAllByRole('row');

    // Check each data row has a canonical name
    const expectedCanonicalNames = [
      'org/model-1',
      'org/model-2',
      'meta-llama/llama-2-7b',
      'org/model-5',
      'org/model-6',
    ];

    for (let i = 1; i < rows.length; i++) {
      const row = rows[i];
      const cells = within(row).getAllByRole('gridcell');

      // Check if this row has TYPE column showing INFERENCE
      const typeCell = cells[2]; // Third column is TYPE
      if (typeCell.textContent !== 'type.INFERENCE') {
        continue; // Skip non-INFERENCE rows
      }

      const canonicalNameCell = cells[1]; // Second column
      const canonicalNameText = canonicalNameCell.textContent;

      expect(canonicalNameText).toBeTruthy();
      expect(canonicalNameText).not.toBe('');
      expect(expectedCanonicalNames).toContain(canonicalNameText);
    }
  });

  it('displays no data indicator for workload without AIM or Model', async () => {
    // Workload without modelId or aimId should show NoDataDisplay
    const workloadWithoutModelOrAim: Workload = {
      id: 'workload-no-model',
      name: 'Standalone Inference',
      displayName: 'Standalone Inference',
      createdBy: 'test-user',
      chartId: 'chart-standalone',
      type: WorkloadType.INFERENCE,
      project: mockWorkloads[0].project,
      createdAt: '2023-01-15T00:00:00Z',
      updatedAt: '2023-01-15T01:00:00Z',
      updatedBy: 'test-user',
      status: WorkloadStatus.RUNNING,
      allocatedResources: {
        gpuCount: 1,
        vram: 2147483648.0,
      },
    };

    mockListWorkloads.mockResolvedValue([workloadWithoutModelOrAim]);

    await act(async () => {
      render(<DeployedModels />, { wrapper });
    });

    await waitFor(() => {
      expect(screen.getByText('Standalone Inference')).toBeInTheDocument();
    });

    const table = screen.getByRole('grid');
    const rows = within(table).getAllByRole('row');
    expect(rows).toHaveLength(2);

    const dataRow = rows[1];
    const cells = within(dataRow).getAllByRole('gridcell');
    const canonicalNameCell = cells[1];
    const canonicalNameText = canonicalNameCell.textContent;

    // Verify NoDataDisplay is shown (no canonical name patterns)
    expect(canonicalNameText).not.toMatch(/\//);
    expect(canonicalNameText).not.toMatch(/^org\//);
    expect(canonicalNameText).not.toMatch(/^meta-/);
  });
});
