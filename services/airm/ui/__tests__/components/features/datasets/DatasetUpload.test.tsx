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

import { getDatasets } from '@/services/app/datasets';

import { DatasetUpload } from '@/components/features/datasets/DatasetUpload';

import wrapper from '@/__tests__/ProviderWrapper';
import { Mock } from 'vitest';

vi.mock('@/services/app/datasets', () => ({
  getDatasets: vi.fn(),
  uploadDataset: vi.fn(),
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

vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// Mock the project context
vi.mock('@/contexts/ProjectContext', () => ({
  useProject: () => ({
    activeProject: 'project1',
    projects: [{ id: 'project1', name: 'Project 1' }],
    isLoading: false,
    setActiveProject: vi.fn(),
  }),
}));

describe('DatasetUpload', () => {
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the dataset upload modal correctly', async () => {
    await act(async () => {
      render(
        <DatasetUpload isOpen={true} refresh={vi.fn()} onClose={mockOnClose} />,
        { wrapper },
      );
    });

    expect(screen.getByText('modals.upload.title')).toBeInTheDocument();
    expect(
      screen.getByLabelText('modals.upload.form.datasetName.label'),
    ).toBeInTheDocument();
    expect(screen.getByTestId('datasetSelect')).toBeInTheDocument();
    expect(
      screen.getByLabelText('modals.upload.form.description.label'),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText('modals.upload.form.fileUpload.label'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('modals.upload.form.fileUpload.placeholder'),
    ).toBeInTheDocument();
  });

  it('validates dataset name is unique', async () => {
    (getDatasets as Mock).mockResolvedValue([]);

    await act(async () => {
      render(
        <DatasetUpload isOpen={true} refresh={vi.fn()} onClose={mockOnClose} />,
        { wrapper },
      );
    });

    const nameInput = screen.getByLabelText(
      'modals.upload.form.datasetName.label',
    );
    await act(async () => {
      fireEvent.change(nameInput, { target: { value: 'unique-name' } });
      fireEvent.blur(nameInput);
    });

    await waitFor(() => {
      expect(getDatasets).toHaveBeenCalledWith('project1', {
        name: 'unique-name',
      });
    });
  });

  it('validates file type', async () => {
    await act(async () => {
      render(
        <DatasetUpload isOpen={true} refresh={vi.fn()} onClose={mockOnClose} />,
        { wrapper },
      );
    });

    const invalidFile = new File(['test content'], 'test.txt', {
      type: 'text/plain',
    });
    const fileInput = screen.getByLabelText(
      'modals.upload.form.fileUpload.label',
    ) as HTMLInputElement;

    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [invalidFile] } });
    });

    // Check for file type error message in the DOM (i18n key)
    expect(
      screen.getByText('modals.upload.form.fileUpload.formatError'),
    ).toBeInTheDocument();
  });
});
