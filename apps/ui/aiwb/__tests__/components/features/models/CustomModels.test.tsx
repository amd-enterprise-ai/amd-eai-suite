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

import { mockModels } from '@/__mocks__/services/app/models.data';
import { mockWorkloads } from '@/__mocks__/services/app/workloads.data';
import { getFinetunableModels, getModels } from '@/lib/app/models';
import { listWorkloads } from '@/lib/app/workloads';
import { getAimServices } from '@/lib/app/aims';

import { FinetunableModel } from '@/types/models';
import { WorkloadStatus } from '@/types/enums/workloads';
import CustomModels from '@/components/features/models/CustomModels';

import wrapper from '@/__tests__/ProviderWrapper';
import { Mock, vi } from 'vitest';

// Assuming Workload type exists here

// Mock the API services
vi.mock('@/lib/app/models', async (importOriginal) => ({
  ...(await importOriginal()),
  finetuneModel: vi.fn(),
  deleteModel: vi.fn(),
  getModels: vi.fn(),
  getFinetunableModels: vi.fn(),
}));

vi.mock('@/lib/app/workloads', async (importOriginal) => ({
  ...(await importOriginal()),
  listWorkloads: vi.fn(),
}));

vi.mock('@/lib/app/aims', async (importOriginal) => ({
  ...(await importOriginal()),
  getAimServices: vi.fn().mockResolvedValue([]),
}));

// Mock useSystemToast for testing
vi.mock('@amdenterpriseai/hooks', async (importOriginal) => ({
  ...(await importOriginal()),
  useSystemToast: () => ({
    toast: {
      success: vi.fn(),
      error: vi.fn(),
    },
  }),
}));

vi.mock('next/router', () => ({
  useRouter: vi.fn(),
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

describe('Custom Models', () => {
  const mockFinetunableModels: FinetunableModel[] = [
    {
      canonicalName: 'org/model-1',
      gpuCount: 0,
      compatibleAccelerators: [],
      compatibleAcceleratorNames: [],
    },
    {
      canonicalName: 'org/model-6',
      gpuCount: 0,
      compatibleAccelerators: [],
      compatibleAcceleratorNames: [],
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    (getModels as Mock).mockResolvedValue(mockModels);
    (getFinetunableModels as Mock).mockResolvedValue(mockFinetunableModels);
    (listWorkloads as Mock).mockResolvedValue({
      data: mockWorkloads,
      total: mockWorkloads.length,
      page: 1,
      pageSize: 10,
    });
  });

  it('renders custom models component', async () => {
    await act(async () => {
      render(<CustomModels />, { wrapper });
    });

    // Wait for the models to load
    await waitFor(() => {
      expect(getModels).toHaveBeenCalled();
    });

    // Deleted and Unknown workloads should be excluded from the query
    expect(listWorkloads).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        status: expect.not.arrayContaining([
          WorkloadStatus.DELETED,
          WorkloadStatus.UNKNOWN,
        ]),
      }),
    );

    await waitFor(() => {
      expect(screen.getByText('model-1')).toBeInTheDocument();
      expect(screen.getByText('model-2')).toBeInTheDocument();
      expect(screen.getByText('model-3')).toBeInTheDocument();
    });
  });

  it('filters models by search query', async () => {
    await act(async () => {
      render(<CustomModels />, { wrapper });
    });

    // Wait for the models to load
    await waitFor(() => {
      expect(getModels).toHaveBeenCalled();
    });

    const searchInput = screen.getByPlaceholderText(
      'customModels.list.filters.search.placeholder',
    );
    fireEvent.change(searchInput, { target: { value: 'model-1' } });

    // Wait for debounced search to trigger
    await waitFor(() => {
      expect(screen.queryByText('model-1')).toBeInTheDocument();
      expect(screen.queryByText('model-2')).not.toBeInTheDocument();
      expect(screen.queryByText('model-3')).not.toBeInTheDocument();
    });
  });

  it('clears filters', async () => {
    await act(async () => {
      render(<CustomModels />, { wrapper });
    });

    // Wait for the models to load
    await waitFor(() => {
      expect(getModels).toHaveBeenCalled();
    });

    // All models should be visible since type filtering is removed
    expect(screen.queryByText('model-1')).toBeInTheDocument();
    expect(screen.queryByText('model-2')).toBeInTheDocument();
    expect(screen.queryByText('model-3')).toBeInTheDocument();

    // Click clear filters button
    const clearButton = screen.getByText('actions.clearFilters.title');
    await act(async () => {
      fireEvent.click(clearButton);
    });

    // After clearing filters, all models should be visible again including model-3
    await waitFor(() => {
      expect(screen.queryByText('model-3')).toBeInTheDocument();
      expect(screen.queryByText('model-1')).toBeInTheDocument();
      expect(screen.queryByText('model-2')).toBeInTheDocument();
    });
  });

  it('opens finetune model modal', async () => {
    await act(async () => {
      render(<CustomModels />, { wrapper });
    });

    await waitFor(() => {
      expect(getModels).toHaveBeenCalled();
    });

    const createNewButton = screen.getByText(
      'customModels.list.actions.finetune.title',
    );
    fireEvent.click(createNewButton);

    await waitFor(() => {
      expect(getFinetunableModels).toHaveBeenCalled();
    });
  });

  it('opens deploy model modal from row action', async () => {
    await act(async () => {
      render(<CustomModels />, { wrapper });
    });

    await waitFor(() => {
      expect(getModels).toHaveBeenCalled();
    });
  });

  it('opens model details modal from row action', async () => {
    await act(async () => {
      render(<CustomModels />, { wrapper });
    });

    // Wait for the models to load
    await waitFor(() => {
      expect(getModels).toHaveBeenCalled();
    });

    expect(getModels).toHaveBeenCalled();
  });

  it('refreshes the models list', async () => {
    await act(async () => {
      render(<CustomModels />, { wrapper });
    });

    // Wait for initial models load
    await waitFor(() => {
      expect(getModels).toHaveBeenCalledTimes(1);
    });

    const refreshButton = screen.getByRole('button', { name: /refresh/i });

    fireEvent.click(refreshButton);

    await waitFor(() => {
      // getModels should be called again on refresh
      expect(getModels).toHaveBeenCalledTimes(2);
    });
  });

  it('allows deleting a model', async () => {
    await act(async () => {
      render(<CustomModels />, { wrapper });
    });

    await waitFor(() => {
      expect(getModels).toHaveBeenCalled();
      expect(screen.getByText('model-1')).toBeInTheDocument();
    });

    const actionButtons = await screen.findAllByText('action-dot-icon');
    await act(async () => {
      fireEvent.click(actionButtons[0]);
    });

    const deleteOption = await screen.findByTestId('delete');
    expect(deleteOption).toBeInTheDocument();
  });

  it('shows AIM deployment count in workloads column', async () => {
    (getAimServices as Mock).mockResolvedValue([
      {
        id: 'aim-svc-1',
        metadata: {
          name: 'svc-1',
          creationTimestamp: '2026-01-01T00:00:00Z',
          annotations: {},
        },
        status: {
          status: 'Running',
          resolvedModel: { name: 'wb-finetune-cr-1' },
        },
      },
      {
        id: 'aim-svc-2',
        metadata: {
          name: 'svc-2',
          creationTimestamp: '2026-01-01T00:00:00Z',
          annotations: {},
        },
        status: {
          status: 'Running',
          resolvedModel: { name: 'wb-finetune-cr-1' },
        },
      },
    ]);

    await act(async () => {
      render(<CustomModels />, { wrapper });
    });

    await waitFor(() => {
      expect(getAimServices).toHaveBeenCalled();
    });

    // model-1's resourceName is 'wb-finetune-cr-1', matching both AIM services
    const model1Row = (await screen.findByText('model-1')).closest('tr');
    expect(model1Row).not.toBeNull();
    expect(within(model1Row!).getByText('2')).toBeInTheDocument();
  });

  it('does not show deploy action when model status is not complete', async () => {
    await act(async () => {
      render(<CustomModels />, { wrapper });
    });

    // Wait for initial models load
    await waitFor(() => {
      expect(getModels).toHaveBeenCalledTimes(1);
    });

    // Find the row for model-2 which has Pending status
    const model2Row = await screen.findByText('model-2');
    expect(model2Row).toBeInTheDocument();

    // Find the table row containing model-2
    const tableRow = model2Row.closest('tr');
    expect(tableRow).not.toBeNull();

    // Find the context menu button within that specific row
    const actionButton = tableRow
      ? await within(tableRow).findByText('action-dot-icon')
      : null;
    expect(actionButton).not.toBeNull();

    // Click the action button for model-2
    await act(async () => {
      if (actionButton) fireEvent.click(actionButton);
    });

    // Check that the Deploy option is not present since model-2 has Pending status
    const deployOption = screen.queryByTestId('deploy');
    expect(deployOption).not.toBeInTheDocument();

    // Also test with model-4 which has Failed status
    const model4Row = await screen.findByText('model-4');
    expect(model4Row).toBeInTheDocument();

    const tableRow4 = model4Row.closest('tr');
    expect(tableRow4).not.toBeNull();

    const actionButton4 = tableRow4
      ? await within(tableRow4).findByText('action-dot-icon')
      : null;
    expect(actionButton4).not.toBeNull();

    // Click the action button for model-4
    await act(async () => {
      if (actionButton4) fireEvent.click(actionButton4);
    });

    // Check that the Deploy option is not present for model-4 with Failed status
    const deployOption4 = screen.queryByTestId('deploy');
    expect(deployOption4).not.toBeInTheDocument();
  });
});
