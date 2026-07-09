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
import {
  finetuneModel,
  getFinetunableModels,
  listAllProjectFineTunedModels,
} from '@/lib/app/models';
import { listAllWorkloads } from '@/lib/app/workloads';
import { listAllInferenceDeployments } from '@/lib/app/inference';

import { FinetunableModel } from '@/types/models';
import { WorkloadStatus } from '@/types/enums/workloads';
import FineTuneModels from '@/components/features/models/FineTuneModels';

import wrapper from '@/__tests__/ProviderWrapper';
import { Mock, vi } from 'vitest';

// Assuming Workload type exists here

// Mock the API services
vi.mock('@/lib/app/models', async (importOriginal) => ({
  ...(await importOriginal()),
  finetuneModel: vi.fn(),
  deleteModel: vi.fn(),
  listAllProjectFineTunedModels: vi.fn(),
  getFinetunableModels: vi.fn(),
}));

vi.mock('@/lib/app/workloads', async (importOriginal) => ({
  ...(await importOriginal()),
  listAllWorkloads: vi.fn(),
}));

vi.mock('@/lib/app/inference', () => ({
  listAllInferenceDeployments: vi.fn().mockResolvedValue([]),
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

describe('Fine-tune models', () => {
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
    vi.resetAllMocks();
    (finetuneModel as Mock).mockResolvedValue({
      id: 'new-finetune-workload',
      name: 'new-model',
    });
    (listAllProjectFineTunedModels as Mock).mockResolvedValue(mockModels);
    (getFinetunableModels as Mock).mockResolvedValue(mockFinetunableModels);
    (listAllWorkloads as Mock).mockResolvedValue(mockWorkloads);
    (listAllInferenceDeployments as Mock).mockResolvedValue([]);
  });

  it('renders the fine-tuned models table and excludes deleted/unknown workloads from the query', async () => {
    await act(async () => {
      render(<FineTuneModels />, { wrapper });
    });

    // Wait for the models to load
    await waitFor(() => {
      expect(listAllProjectFineTunedModels).toHaveBeenCalled();
    });

    // Deleted and Unknown workloads should be excluded from the query
    expect(listAllWorkloads).toHaveBeenCalledWith(
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
      render(<FineTuneModels />, { wrapper });
    });

    // Wait for the models to load
    await waitFor(() => {
      expect(listAllProjectFineTunedModels).toHaveBeenCalled();
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
      render(<FineTuneModels />, { wrapper });
    });

    // Wait for the models to load
    await waitFor(() => {
      expect(listAllProjectFineTunedModels).toHaveBeenCalled();
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
      render(<FineTuneModels />, { wrapper });
    });

    await waitFor(() => {
      expect(listAllProjectFineTunedModels).toHaveBeenCalled();
    });

    const createNewButton = screen.getByText(
      'customModels.list.actions.finetune.title',
    );
    fireEvent.click(createNewButton);

    await waitFor(() => {
      expect(getFinetunableModels).toHaveBeenCalled();
    });
  });

  it('refreshes the models list', async () => {
    await act(async () => {
      render(<FineTuneModels />, { wrapper });
    });

    // Wait for initial models load
    await waitFor(() => {
      expect(listAllProjectFineTunedModels).toHaveBeenCalledTimes(1);
    });

    const refreshButton = screen.getByRole('button', { name: /refresh/i });

    fireEvent.click(refreshButton);

    await waitFor(() => {
      // listAllProjectFineTunedModels should be called again on refresh
      expect(listAllProjectFineTunedModels).toHaveBeenCalledTimes(2);
    });
  });

  it('allows deleting a model', async () => {
    await act(async () => {
      render(<FineTuneModels />, { wrapper });
    });

    await waitFor(() => {
      expect(listAllProjectFineTunedModels).toHaveBeenCalled();
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
    (listAllInferenceDeployments as Mock).mockResolvedValue([
      {
        id: 'aim-svc-1',
        metadata: {
          name: 'svc-1',
          creationTimestamp: '2026-01-01T00:00:00Z',
          annotations: {},
        },
        spec: { model: { name: 'wb-finetune-cr-1' } },
        status: {
          status: 'Running',
        },
      },
      {
        id: 'aim-svc-2',
        metadata: {
          name: 'svc-2',
          creationTimestamp: '2026-01-01T00:00:00Z',
          annotations: {},
        },
        spec: { model: { name: 'wb-finetune-cr-1' } },
        status: {
          status: 'Running',
        },
      },
    ]);

    await act(async () => {
      render(<FineTuneModels />, { wrapper });
    });

    await waitFor(() => {
      expect(listAllInferenceDeployments).toHaveBeenCalled();
    });

    // model-1's resourceName is 'wb-finetune-cr-1', matching both AIM services
    const model1Row = (await screen.findByText('model-1')).closest('tr');
    expect(model1Row).not.toBeNull();
    expect(within(model1Row!).getByText('2')).toBeInTheDocument();
  });

  it('renders pending fine-tuning rows with the user-chosen name and a no-data canonical column', async () => {
    await act(async () => {
      render(<FineTuneModels />, { wrapper });
    });

    await waitFor(() => {
      expect(listAllProjectFineTunedModels).toHaveBeenCalled();
      expect(listAllWorkloads).toHaveBeenCalled();
    });

    // workload-6 is a Pending FINE_TUNING workload whose internal k8s name is
    // 'Fine-tuning Workload with Dataset' and whose user-chosen displayName is
    // 'Fine-tuning Model with Dataset'. The Name column must show displayName.
    const displayNameCell = await screen.findByText(
      'Fine-tuning Model with Dataset',
    );
    expect(displayNameCell).toBeInTheDocument();

    const row = displayNameCell.closest('tr');
    expect(row).not.toBeNull();

    // Resource (k8s) name must NOT leak into the Name column.
    expect(
      within(row!).queryByText('Fine-tuning Workload with Dataset'),
    ).not.toBeInTheDocument();

    // Canonical Name cell must render the no-data placeholder (em dash),
    // not the displayName (the previous bug rendered displayName here).
    expect(within(row!).getByText('\u2014')).toBeInTheDocument();
    // The displayName must appear exactly once in the row (in the Name cell),
    // not duplicated into the Canonical Name cell.
    expect(
      within(row!).getAllByText('Fine-tuning Model with Dataset'),
    ).toHaveLength(1);
  });

  it('does not show deploy action when model status is not complete', async () => {
    await act(async () => {
      render(<FineTuneModels />, { wrapper });
    });

    // Wait for initial models load
    await waitFor(() => {
      expect(listAllProjectFineTunedModels).toHaveBeenCalledTimes(1);
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

  it('shows fine-tune action for completed custom model rows', async () => {
    await act(async () => {
      render(<FineTuneModels />, { wrapper });
    });

    await waitFor(() => {
      expect(listAllProjectFineTunedModels).toHaveBeenCalled();
    });

    const model1Row = (await screen.findByText('model-1')).closest('tr');
    expect(model1Row).not.toBeNull();

    const actionButton = model1Row
      ? await within(model1Row).findByText('action-dot-icon')
      : null;
    expect(actionButton).not.toBeNull();

    await act(async () => {
      if (actionButton) fireEvent.click(actionButton);
    });

    expect(await screen.findByTestId('finetune')).toBeInTheDocument();
  });

  it('opens fine-tune drawer from completed model action with locked base model', async () => {
    await act(async () => {
      render(<FineTuneModels />, { wrapper });
    });

    await waitFor(() => {
      expect(listAllProjectFineTunedModels).toHaveBeenCalled();
    });

    const model1Row = (await screen.findByText('model-1')).closest('tr');
    expect(model1Row).not.toBeNull();

    const actionButton = model1Row
      ? await within(model1Row).findByText('action-dot-icon')
      : null;
    expect(actionButton).not.toBeNull();

    await act(async () => {
      if (actionButton) fireEvent.click(actionButton);
    });

    fireEvent.click(await screen.findByTestId('finetune'));

    const baseModelSelectButton = screen.getByRole('button', {
      name: /list\.actions\.finetune\.modal\.baseModel\.label/i,
    });

    expect(baseModelSelectButton).toHaveTextContent('model-1');
    expect(baseModelSelectButton).toHaveAttribute('data-disabled', 'true');
    expect(
      screen.queryByRole('button', {
        name: /huggingFaceTokenDrawer\.fields\.selectToken\.label/i,
      }),
    ).not.toBeInTheDocument();
  });
});
