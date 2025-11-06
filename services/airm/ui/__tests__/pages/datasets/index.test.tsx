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

import { mockDatasets } from '@/__mocks__/services/app/datasets.data';
import {
  deleteDatasets,
  downloadDatasetById,
  getDatasets,
} from '@/services/app/datasets';

import DatasetsPage from '@/pages/datasets';

import wrapper from '@/__tests__/ProviderWrapper';
import { Mock, vi } from 'vitest';

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

// Update the mock to include getDatasets
vi.mock('@/services/app/datasets', () => ({
  downloadDatasetById: vi.fn(),
  deleteDatasets: vi.fn(),
  getDatasets: vi.fn(),
}));

describe('Datasets Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (getDatasets as Mock).mockResolvedValue(mockDatasets);
  });

  it('renders the datasets page', async () => {
    await act(async () => {
      render(<DatasetsPage />, { wrapper });
    });

    await waitFor(() => {
      expect(screen.getByText('dataset-1')).toBeInTheDocument();
      expect(screen.getByText('dataset-2')).toBeInTheDocument();
    });
  });

  it('allows filtering datasets', async () => {
    await act(async () => {
      render(<DatasetsPage />, { wrapper });
    });

    const filterButton = screen.getByText('actions.datasetTypeFilter');
    await act(async () => {
      fireEvent.click(filterButton);
    });

    const evaluationOption = await screen.findAllByText('types.Evaluation');
    await act(async () => {
      fireEvent.click(evaluationOption[0]);
    });

    expect(screen.getByText('dataset-2')).toBeInTheDocument();
  });

  it('allows downloading a dataset', async () => {
    await act(async () => {
      render(<DatasetsPage />, { wrapper });
    });

    await waitFor(() => {
      expect(screen.getByText('dataset-1')).toBeInTheDocument();
    });

    const actionButtons = await screen.findAllByText('action-dot-icon');
    await act(async () => {
      fireEvent.click(actionButtons[0]);
    });

    const downloadOption = await screen.findByTestId('download');
    await act(async () => {
      fireEvent.click(downloadOption);
    });

    await waitFor(() => {
      // downloadDatasetById(id, activeProject)
      expect(downloadDatasetById).toHaveBeenCalledWith('1', 'project1');
    });
  });

  it('allows deleting a dataset', async () => {
    await act(async () => {
      render(<DatasetsPage />, { wrapper });
    });

    await waitFor(() => {
      expect(screen.getByText('dataset-1')).toBeInTheDocument();
    });

    const actionButtons = await screen.findAllByText('action-dot-icon');
    await act(async () => {
      fireEvent.click(actionButtons[0]);
    });

    const deleteOption = await screen.findByTestId('delete');
    await act(async () => {
      fireEvent.click(deleteOption);
    });

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    const confirmButton = screen.getByRole('button', {
      name: /confirm/i,
    });
    await act(async () => {
      fireEvent.click(confirmButton);
    });

    await waitFor(() => {
      // deleteDatasets(ids, activeProject)
      expect(deleteDatasets).toHaveBeenCalledWith(['1'], 'project1');
    });
  });
});
