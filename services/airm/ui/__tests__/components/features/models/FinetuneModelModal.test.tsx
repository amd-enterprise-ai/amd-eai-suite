// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useQuery } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { DEFAULT_FINETUNE_PARAMS } from '@/utils/app/models';

import { Dataset, DatasetType } from '@/types/datasets';
import { Model, ModelOnboardingStatus } from '@/types/models';

import FinetuneModelModal from '@/components/features/models/FinetuneModelModal';

import { Mock, beforeEach, describe, expect, it, vi } from 'vitest';
import wrapper from '@/__tests__/ProviderWrapper';

// Mock next-i18next
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key, // Simple pass-through mock
  }),
}));

// Mock @tanstack/react-query's useQuery and useQueryClient
vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-query')>();
  return {
    ...actual,
    useQuery: vi.fn(),
    useQueryClient: vi.fn(() => ({
      fetchQuery: vi.fn().mockResolvedValue([]), // Mock fetchQuery to return empty array (no models with that name)
    })),
  };
});

// Mock lodash/debounce to execute immediately and include other lodash functions
vi.mock('lodash', async (importOriginal) => {
  const actual = await importOriginal<typeof import('lodash')>();
  return {
    ...actual,
    debounce: (fn: (...args: any[]) => any) => fn,
    snakeCase: actual.snakeCase, // Keep the original snakeCase function
  };
});

// Mock the services
vi.mock('@/services/app/models', () => ({
  getModels: vi.fn(),
}));

vi.mock('@/services/app/datasets', () => ({
  getDatasets: vi.fn(),
}));

const mockBaseModel1: Model = {
  id: 'base-1',
  name: 'Base_Model_One',
  createdAt: '2023-01-01T00:00:00Z',
  modelWeightsPath: '/path/base1',
  createdBy: 'Base Author',
  onboardingStatus: ModelOnboardingStatus.READY,
  canonicalName: 'base-org/base-model-one',
};

const mockBaseModel2: Model = {
  id: 'base-2',
  name: 'Base_Model_Two',
  createdAt: '2023-01-02T00:00:00Z',
  modelWeightsPath: '/path/base2',
  createdBy: 'Base Author 2',
  onboardingStatus: ModelOnboardingStatus.READY,
  canonicalName: 'base-org/base-model-two',
};

const mockBaseModel3: Model = {
  id: 'base-3',
  name: 'Failed_Base_Model_Three',
  createdAt: '2023-01-02T00:00:00Z',
  modelWeightsPath: '/path/base2',
  createdBy: 'Base Author 2',
  onboardingStatus: ModelOnboardingStatus.FAILED,
  canonicalName: 'base-org/base-model-three',
};

const mockBaseModel4: Model = {
  id: 'base-4',
  name: 'Pending_Base_Model_Four',
  createdAt: '2023-01-02T00:00:00Z',
  modelWeightsPath: '/path/base2',
  createdBy: 'Base Author 4',
  onboardingStatus: ModelOnboardingStatus.PENDING,
  canonicalName: 'base-org/base-model-four',
};

const mockFinetunedModel: Model = {
  id: 'finetuned-1',
  name: 'Existing_Finetuned_Model',
  createdAt: '2023-01-03T00:00:00Z',
  modelWeightsPath: '/path/finetuned1',
  createdBy: 'Finetune Author',
  onboardingStatus: ModelOnboardingStatus.READY,
  canonicalName: 'finetune-org/existing-finetuned-model',
};

const mockFinetunedModelWithInvalidCharacters: Model = {
  id: 'finetuned-2',
  name: 'Finetuned Model With Invalid Characters !@#',
  createdAt: '2023-01-03T00:00:00Z',
  modelWeightsPath: '/path/finetuned1',
  createdBy: 'Finetune Author',
  onboardingStatus: ModelOnboardingStatus.READY,
  canonicalName: 'finetune-org/finetuned-model-invalid',
};

const mockModels: Model[] = [
  mockBaseModel1,
  mockBaseModel2,
  mockBaseModel3,
  mockBaseModel4,
  mockFinetunedModel,
  mockFinetunedModelWithInvalidCharacters,
];

const mockDataset1: Dataset = {
  id: 'dataset-1',
  name: 'Finetuning Dataset One',
  type: DatasetType.Finetuning,
  createdAt: '2023-01-01T00:00:00Z',
  path: '/path/dataset1',
  createdBy: 'Author',
  updatedAt: '',
  description: '',
};

const mockDataset2: Dataset = {
  id: 'dataset-2',
  name: 'Finetuning Dataset Two',
  type: DatasetType.Finetuning,
  createdAt: '2023-01-02T00:00:00Z',
  path: '/path/dataset2',
  createdBy: 'Author 2',
  updatedAt: '',
  description: '',
};

const mockDatasets: Dataset[] = [mockDataset1, mockDataset2];

vi.mock('@/services/app/projects', () => ({
  fetchSubmittableProjects: vi.fn(() =>
    Promise.resolve({
      projects: [{ id: 'project1', name: 'Project 1' }],
    }),
  ),
}));
describe('FinetuneModelModal', () => {
  let onOpenChangeMock: ReturnType<typeof vi.fn>;
  let onConfirmActionMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    onOpenChangeMock = vi.fn();
    onConfirmActionMock = vi.fn();

    // Mock useQuery return value for datasets, models, and finetunable models
    (useQuery as Mock).mockImplementation(({ queryKey }) => {
      if (queryKey[0] === 'project' && queryKey[2] === 'datasets') {
        return {
          data: mockDatasets,
          isLoading: false,
          isError: false,
          isSuccess: true,
        };
      }
      if (
        queryKey[0] === 'project' &&
        queryKey[2] === 'models' &&
        !queryKey[3]
      ) {
        return {
          data: mockModels,
          isLoading: false,
          isError: false,
          isSuccess: true,
        };
      }
      if (queryKey[0] === 'project' && queryKey[2] === 'secrets') {
        return {
          data: [
            {
              id: 'project-secret-1',
              name: 'Test HF Project Secret',
              projectId: 'project-1',
              projectName: 'Test Project',
              displayName: 'Test HF Token',
              scope: 'Project',
              status: 'Synced',
              statusReason: '',
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
              createdBy: 'user-1',
              updatedBy: 'user-1',
              secret: {
                id: 'hf-secret-1',
                name: 'Test HF Secret',
                displayName: 'Test HF Token',
                type: 'External',
                status: 'Pending',
                statusReason: '',
                scope: 'Organization',
                useCase: 'HuggingFace',
                projectSecrets: [],
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString(),
              },
            },
          ],
          isLoading: false,
          isError: false,
          isSuccess: true,
        };
      }

      return {
        data: [],
        isLoading: false,
        isError: false,
        isSuccess: true,
      };
    });
  });

  const renderComponent = (
    props: Partial<React.ComponentProps<typeof FinetuneModelModal>>,
  ) => {
    const defaultProps: React.ComponentProps<typeof FinetuneModelModal> = {
      isOpen: true,
      onOpenChange: onOpenChangeMock,
      onConfirmAction: onConfirmActionMock,
      model: undefined,
      finetunableModels: [
        mockBaseModel1.canonicalName,
        mockBaseModel2.canonicalName,
      ],
    };
    return render(<FinetuneModelModal {...defaultProps} {...props} />, {
      wrapper,
    });
  };

  it('should not render if isOpen is false', () => {
    renderComponent({ isOpen: false });
    expect(
      screen.queryByText('list.actions.finetune.modal.title'),
    ).not.toBeInTheDocument();
  });

  it('should render the modal with title and form elements when open', () => {
    renderComponent({});
    expect(
      screen.getByText('list.actions.finetune.modal.title'),
    ).toBeInTheDocument();
    expect(screen.getByTestId('baseModelSelect')).toBeInTheDocument();
    expect(screen.getByTestId('datasetSelect')).toBeInTheDocument();
    expect(
      screen.getByLabelText('list.actions.finetune.modal.modelName.label'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('list.actions.finetune.modal.cancel'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('list.actions.finetune.modal.confirm'),
    ).toBeInTheDocument();
  });

  it('should filter and display only ready models in the dropdown', async () => {
    renderComponent({});
    const baseModelSelect = screen.getByTestId('baseModelSelect');
    fireEvent.click(baseModelSelect);

    await waitFor(() => {
      expect(
        screen.queryAllByText(mockBaseModel1.canonicalName).length,
      ).toBeGreaterThan(0);
      expect(
        screen.queryAllByText(mockBaseModel2.canonicalName).length,
      ).toBeGreaterThan(0);
    });

    expect(
      screen.queryByText(mockFinetunedModel.canonicalName),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(mockBaseModel3.canonicalName),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(mockBaseModel4.canonicalName),
    ).not.toBeInTheDocument();
  });

  it('should pre-select the base model if provided', () => {
    renderComponent({ model: mockBaseModel1 });
    // Check the button associated with the select for the displayed value
    const baseModelSelectButton = screen.getByRole('button', {
      name: /list\.actions\.finetune\.modal\.baseModel\.label/i,
    });
    expect(baseModelSelectButton).toHaveTextContent(mockBaseModel1.name);
  });

  it('should call onOpenChange with false when cancel button is clicked', () => {
    renderComponent({});
    const cancelButton = screen.getByText('list.actions.finetune.modal.cancel');
    fireEvent.click(cancelButton);
    expect(onConfirmActionMock).not.toHaveBeenCalled();
    expect(onOpenChangeMock).toHaveBeenCalledTimes(1);
    expect(onOpenChangeMock).toHaveBeenCalledWith(false);
  });

  it('should call onConfirmAction and onOpenChange on valid form submission with default params', async () => {
    renderComponent({});

    const baseModelSelect = screen.getByTestId('baseModelSelect');
    fireEvent.click(baseModelSelect);
    fireEvent.click(
      await screen.findByTestId(`model-select-${mockBaseModel1.canonicalName}`),
    );

    const datasetSelect = screen.getByTestId('datasetSelect');
    fireEvent.click(datasetSelect);
    fireEvent.click(
      await screen.findByTestId(`dataset-select-${mockDataset1.id}`),
    );

    // Allow time for dataset dropdown to stabilize
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Enter Model Name
    const nameInput = screen.getByLabelText(
      'list.actions.finetune.modal.modelName.label',
    );
    fireEvent.change(nameInput, { target: { value: 'New_Finetuned_Model' } });

    // Select existing HuggingFace token from dropdown
    await waitFor(() => {
      expect(
        screen.getByRole('button', {
          name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
        }),
      ).toBeInTheDocument();
    });

    const tokenSelect = screen.getByRole('button', {
      name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
    });
    fireEvent.click(tokenSelect);

    await waitFor(() => {
      expect(
        screen.getByRole('option', { name: 'Test HF Token' }),
      ).toBeInTheDocument();
    });

    const tokenOption = screen.getByRole('option', { name: 'Test HF Token' });
    fireEvent.click(tokenOption);

    // Submit Form
    const confirmButton = screen.getByText(
      'list.actions.finetune.modal.confirm',
    );
    fireEvent.click(confirmButton);

    // Assertions
    await waitFor(() => {
      expect(onConfirmActionMock).toHaveBeenCalledTimes(1);
      expect(onConfirmActionMock).toHaveBeenCalledWith({
        id: encodeURIComponent(mockBaseModel1.canonicalName),
        params: {
          name: 'New_Finetuned_Model',
          datasetId: mockDataset1.id,
          epochs: DEFAULT_FINETUNE_PARAMS.epochs,
          learningRate: DEFAULT_FINETUNE_PARAMS.learningRate,
          batchSize: DEFAULT_FINETUNE_PARAMS.batchSize,
          hfTokenSecretId: 'hf-secret-1',
        },
      });
      expect(onOpenChangeMock).toHaveBeenCalledTimes(1);
      expect(onOpenChangeMock).toHaveBeenCalledWith(false);
    });
  });

  it('should show validation error for empty name', async () => {
    renderComponent({});
    const nameInput = screen.getByLabelText(
      'list.actions.finetune.modal.modelName.label',
    );

    fireEvent.change(nameInput, { target: { value: 'a' } }); // Trigger validation check
    fireEvent.change(nameInput, { target: { value: '' } }); // Make it empty

    await waitFor(() => {
      expect(
        screen.getByText(
          'list.actions.finetune.modal.modelName.emptyNameError',
        ),
      ).toBeInTheDocument();
    });
    expect(nameInput).toBeInvalid();
  });

  it('should show validation error for non-unique name', async () => {
    // Mock the queryClient fetchQuery to return a model with the same name
    const mockQueryClient = {
      fetchQuery: vi.fn().mockResolvedValue([mockFinetunedModel]), // Return existing model
    };

    // Override the useQueryClient mock for this test
    const { useQueryClient } = await import('@tanstack/react-query');
    (useQueryClient as Mock).mockReturnValue(mockQueryClient);

    renderComponent({});

    const nameInput = screen.getByLabelText(
      'list.actions.finetune.modal.modelName.label',
    );

    // Type the name that already exists
    fireEvent.change(nameInput, {
      target: { value: mockFinetunedModel.name },
    });

    // Wait for debounced validation to complete
    await waitFor(
      () => {
        expect(
          screen.getByText(
            'list.actions.finetune.modal.modelName.nonUniqueNameError',
          ),
        ).toBeInTheDocument();
      },
      { timeout: 1000 },
    ); // Give more time for debounced validation

    expect(nameInput).toBeInvalid();
  });

  it('should show validation error for invalid characters in name', async () => {
    renderComponent({});
    const nameInput = screen.getByLabelText(
      'list.actions.finetune.modal.modelName.label',
    );

    fireEvent.change(nameInput, {
      target: { value: mockFinetunedModelWithInvalidCharacters.name },
    });

    await waitFor(() => {
      expect(
        screen.getByText(
          'list.actions.finetune.modal.modelName.invalidCharactersError',
        ),
      ).toBeInTheDocument();
    });
    expect(nameInput).toBeInvalid();
  });

  it('should submit with custom advanced parameters', async () => {
    renderComponent({});

    // Fill required fields
    const baseModelSelect = screen.getByTestId('baseModelSelect');
    fireEvent.click(baseModelSelect);
    fireEvent.click(
      await screen.findByTestId(`model-select-${mockBaseModel1.canonicalName}`),
    );

    const datasetSelect = screen.getByTestId('datasetSelect');
    fireEvent.click(datasetSelect);
    fireEvent.click(
      await screen.findByTestId(`dataset-select-${mockDataset1.id}`),
    );

    // Wait for dataset dropdown to close
    await waitFor(() => {
      expect(
        screen.queryByRole('listbox', {
          name: /list.actions.finetune.modal.dataset.label/i,
        }),
      ).not.toBeInTheDocument();
    });

    // Enter Model Name
    const modelNameInput = screen.getByLabelText(
      'list.actions.finetune.modal.modelName.label',
    );
    fireEvent.change(modelNameInput, { target: { value: 'Advanced_Model' } });

    // Select existing HuggingFace token from dropdown
    await waitFor(
      () => {
        expect(
          screen.getByRole('button', {
            name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
          }),
        ).toBeInTheDocument();
      },
      { timeout: 5000 },
    );

    const tokenSelect = screen.getByRole('button', {
      name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
    });
    fireEvent.click(tokenSelect);

    await waitFor(() => {
      expect(
        screen.getByRole('option', { name: 'Test HF Token' }),
      ).toBeInTheDocument();
    });

    const tokenOption = screen.getByRole('option', { name: 'Test HF Token' });
    fireEvent.click(tokenOption);

    // Wait for token dropdown to close before proceeding
    await waitFor(() => {
      expect(
        screen.queryByRole('listbox', {
          name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
        }),
      ).not.toBeInTheDocument();
    });

    // Open accordion
    const accordionButton = screen.getByText(
      'list.actions.finetune.modal.advancedSettingsAccordion.title',
    );
    fireEvent.click(accordionButton);

    // Wait for accordion to open
    await waitFor(() => {
      expect(
        screen.getByLabelText('list.actions.finetune.modal.batchSize.label'),
      ).toBeInTheDocument();
    });

    // Change advanced settings with proper event handling for NumberInput
    const batchSizeInput = screen.getByLabelText(
      'list.actions.finetune.modal.batchSize.label',
    );
    fireEvent.change(batchSizeInput, { target: { value: '16' } });
    fireEvent.blur(batchSizeInput);

    const learningRateInput = screen.getByLabelText(
      'list.actions.finetune.modal.learningRateMultiplier.label',
    );
    fireEvent.change(learningRateInput, { target: { value: '0.5' } });
    fireEvent.blur(learningRateInput);

    const epochsInput = screen.getByLabelText(
      'list.actions.finetune.modal.epochs.label',
    );
    fireEvent.change(epochsInput, { target: { value: '5' } });
    fireEvent.blur(epochsInput);

    // Wait for any async form updates
    await waitFor(() => {
      expect(batchSizeInput).toHaveValue('16');
    });

    // Submit Form
    const confirmButton = screen.getByText(
      'list.actions.finetune.modal.confirm',
    );
    fireEvent.click(confirmButton);

    // Assertions
    await waitFor(() => {
      expect(onConfirmActionMock).toHaveBeenCalledTimes(1);
      expect(onConfirmActionMock).toHaveBeenCalledWith({
        id: encodeURIComponent(mockBaseModel1.canonicalName),
        params: {
          name: 'Advanced_Model',
          datasetId: mockDataset1.id,
          epochs: 5,
          learningRate: 0.5,
          batchSize: 16,
          hfTokenSecretId: 'hf-secret-1',
        },
      });
      expect(onOpenChangeMock).toHaveBeenCalledTimes(1);
      expect(onOpenChangeMock).toHaveBeenCalledWith(false);
    });
  });

  it('should use model id when model with local weights is provided', async () => {
    renderComponent({ model: mockBaseModel1 });

    const datasetSelect = screen.getByTestId('datasetSelect');
    fireEvent.click(datasetSelect);
    fireEvent.click(
      await screen.findByTestId(`dataset-select-${mockDataset1.id}`),
    );

    // Allow time for dataset dropdown to stabilize
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Enter Model Name
    const nameInput = screen.getByLabelText(
      'list.actions.finetune.modal.modelName.label',
    );
    fireEvent.change(nameInput, { target: { value: 'Model_With_Prop' } });

    // HF Token section should NOT be visible when model has local weights
    expect(
      screen.queryByRole('button', {
        name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
      }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText('huggingFaceTokenDrawer.title'),
    ).not.toBeInTheDocument();

    // Submit Form
    const confirmButton = screen.getByText(
      'list.actions.finetune.modal.confirm',
    );
    fireEvent.click(confirmButton);

    // Assertions - should use model id when model prop is provided
    // and should NOT include hfTokenSecretId since model is available locally
    await waitFor(() => {
      expect(onConfirmActionMock).toHaveBeenCalledTimes(1);
      expect(onConfirmActionMock).toHaveBeenCalledWith({
        id: mockBaseModel1.id, // Should use model id when model prop is provided
        params: {
          name: 'Model_With_Prop',
          datasetId: mockDataset1.id,
          epochs: DEFAULT_FINETUNE_PARAMS.epochs,
          learningRate: DEFAULT_FINETUNE_PARAMS.learningRate,
          batchSize: DEFAULT_FINETUNE_PARAMS.batchSize,
          // No hfTokenSecretId since model is already available locally
        },
      });
      expect(onOpenChangeMock).toHaveBeenCalledTimes(1);
      expect(onOpenChangeMock).toHaveBeenCalledWith(false);
    });
  });

  it('should handle error during model name uniqueness check gracefully', async () => {
    // Mock the queryClient to throw an error
    const mockQueryClient = {
      fetchQuery: vi.fn().mockRejectedValue(new Error('Network error')),
    };

    const { useQueryClient } = await import('@tanstack/react-query');
    (useQueryClient as Mock).mockReturnValue(mockQueryClient);

    const consoleErrorSpy = vi
      .spyOn(console, 'error')
      .mockImplementation(() => {});

    renderComponent({});

    const nameInput = screen.getByLabelText(
      'list.actions.finetune.modal.modelName.label',
    );

    // Type a name that will trigger the API check
    fireEvent.change(nameInput, { target: { value: 'Test_Model_Name' } });

    // Wait for the debounced API check to complete
    await waitFor(
      () => {
        expect(consoleErrorSpy).toHaveBeenCalledWith(
          'Error checking model name availability:',
          expect.any(Error),
        );
      },
      { timeout: 1000 },
    );

    // The input should still be valid (error is handled gracefully)
    expect(nameInput).not.toBeInvalid();

    consoleErrorSpy.mockRestore();
  });

  it('should render datasets when data is available', () => {
    renderComponent({});

    const datasetSelect = screen.getByTestId('datasetSelect');
    fireEvent.click(datasetSelect);

    // Both datasets should be in the dropdown
    expect(
      screen.getByTestId(`dataset-select-${mockDataset1.id}`),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId(`dataset-select-${mockDataset2.id}`),
    ).toBeInTheDocument();
  });

  it('should show HF Token section when model is undefined (fine-tuning from canonical name)', async () => {
    renderComponent({ model: undefined });

    // HF Token section should be visible
    await waitFor(() => {
      expect(
        screen.getByRole('button', {
          name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
        }),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByText('huggingFaceTokenDrawer.title'),
    ).toBeInTheDocument();
  });

  it('should hide HF Token section when model has local weights', () => {
    renderComponent({ model: mockBaseModel1 });

    // HF Token section should NOT be visible when model has modelWeightsPath
    expect(
      screen.queryByRole('button', {
        name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
      }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText('huggingFaceTokenDrawer.title'),
    ).not.toBeInTheDocument();
  });

  it('should show HF Token section when model has no local weights', async () => {
    const modelWithoutWeights = { ...mockBaseModel1, modelWeightsPath: null };
    renderComponent({ model: modelWithoutWeights });

    // HF Token section should be visible since model has no local weights
    await waitFor(() => {
      expect(
        screen.getByRole('button', {
          name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
        }),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByText('huggingFaceTokenDrawer.title'),
    ).toBeInTheDocument();
  });

  it('should require HF Token when fine-tuning from canonical name (model undefined)', async () => {
    renderComponent({ model: undefined });

    // Fill required fields except HF Token
    const baseModelSelect = screen.getByTestId('baseModelSelect');
    fireEvent.click(baseModelSelect);
    fireEvent.click(
      await screen.findByTestId(`model-select-${mockBaseModel1.canonicalName}`),
    );

    const datasetSelect = screen.getByTestId('datasetSelect');
    fireEvent.click(datasetSelect);
    fireEvent.click(
      await screen.findByTestId(`dataset-select-${mockDataset1.id}`),
    );

    // Wait for dataset dropdown to close
    await waitFor(() => {
      expect(
        screen.queryByRole('listbox', {
          name: /list.actions.finetune.modal.dataset.label/i,
        }),
      ).not.toBeInTheDocument();
    });

    // Enter Model Name
    const nameInput = screen.getByLabelText(
      'list.actions.finetune.modal.modelName.label',
    );
    fireEvent.change(nameInput, { target: { value: 'New_Model_No_Token' } });

    // Verify HF Token section is visible
    await waitFor(() => {
      expect(
        screen.getByRole('button', {
          name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
        }),
      ).toBeInTheDocument();
    });

    // Try to submit without selecting HF Token
    const confirmButton = screen.getByText(
      'list.actions.finetune.modal.confirm',
    );
    fireEvent.click(confirmButton);

    // Wait a bit for validation to process
    await new Promise((resolve) => setTimeout(resolve, 500));

    // onConfirmAction should not be called due to validation error
    // Modal should still be open
    expect(onConfirmActionMock).not.toHaveBeenCalled();
    expect(onOpenChangeMock).not.toHaveBeenCalledWith(false);
    expect(
      screen.getByText('list.actions.finetune.modal.title'),
    ).toBeInTheDocument();
  });

  it('should not require HF Token when fine-tuning model with local weights', async () => {
    renderComponent({ model: mockBaseModel1 });

    // Fill required fields without HF Token (which should not be visible)
    const datasetSelect = screen.getByTestId('datasetSelect');
    fireEvent.click(datasetSelect);
    fireEvent.click(
      await screen.findByTestId(`dataset-select-${mockDataset1.id}`),
    );

    // Enter Model Name
    const nameInput = screen.getByLabelText(
      'list.actions.finetune.modal.modelName.label',
    );
    fireEvent.change(nameInput, {
      target: { value: 'Finetuned_From_Existing' },
    });

    // Submit form without HF Token
    const confirmButton = screen.getByText(
      'list.actions.finetune.modal.confirm',
    );
    fireEvent.click(confirmButton);

    // Should successfully submit without HF Token since model has local weights
    await waitFor(() => {
      expect(onConfirmActionMock).toHaveBeenCalledTimes(1);
      expect(onConfirmActionMock).toHaveBeenCalledWith({
        id: mockBaseModel1.id,
        params: {
          name: 'Finetuned_From_Existing',
          datasetId: mockDataset1.id,
          epochs: DEFAULT_FINETUNE_PARAMS.epochs,
          learningRate: DEFAULT_FINETUNE_PARAMS.learningRate,
          batchSize: DEFAULT_FINETUNE_PARAMS.batchSize,
          // No hfTokenSecretId - not needed since model has local weights
        },
      });
    });
  });
});
