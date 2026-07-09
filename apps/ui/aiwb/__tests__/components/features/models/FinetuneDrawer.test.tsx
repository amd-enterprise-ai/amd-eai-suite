// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { QueryClient, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';

import { Dataset } from '@/types/datasets';
import { DatasetType } from '@/types/datasets';
import { SecretUseCase } from '@amdenterpriseai/types';
import {
  AIM_MODEL_WORKLOAD_ID_LABEL,
  AIM_MODEL_NAME_LABEL,
  AIMModel,
} from '@/types/aims';
import {
  FinetunableModel,
  Model,
  ModelFinetuneParams,
  ModelOnboardingStatus,
} from '@/types/models';

import FinetuneDrawer from '@/components/features/models/FinetuneDrawer';
import { createProjectSecret, fetchProjectSecrets } from '@/lib/app/secrets';
import { listAllProjectFineTunedModels } from '@/lib/app/models';
import { listAllWorkloads } from '@/lib/app/workloads';

import { Mock, beforeEach, describe, expect, it, vi } from 'vitest';
import wrapper from '@/__tests__/ProviderWrapper';
import { SecretResponseData } from '@/types/secrets';

// Mock next-i18next
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key, // Simple pass-through mock
  }),
}));

const mockToast = {
  success: vi.fn(),
  error: vi.fn(),
};

vi.mock('@amdenterpriseai/hooks', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@amdenterpriseai/hooks')>()),
  useSystemToast: () => ({ toast: mockToast }),
}));

// Mock @tanstack/react-query's useQuery and useQueryClient
vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-query')>();
  return {
    ...actual,
    useQuery: vi.fn(),
    useQueryClient: vi.fn(),
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

// Mock local services
vi.mock('@/lib/app/secrets', async (importOriginal) => ({
  ...(await importOriginal()),
  createProjectSecret: vi.fn(),
  fetchProjectSecrets: vi.fn(),
}));

vi.mock('@/lib/app/datasets', () => ({
  getAllDatasets: vi.fn().mockResolvedValue([]),
}));

// Mock shared services
vi.mock('@/lib/app/models', () => ({
  listAllProjectFineTunedModels: vi.fn().mockResolvedValue([]),
}));

vi.mock('@/lib/app/workloads', () => ({
  listAllWorkloads: vi.fn().mockResolvedValue([]),
}));

const mockBaseModel1: Model = {
  id: 'base-1',
  name: 'Base_Model_One',
  createdAt: '2023-01-01T00:00:00Z',
  sourceUri: '/path/base1',
  createdBy: 'Base Author',
  onboardingStatus: ModelOnboardingStatus.READY,
  canonicalName: 'base-org/base-model-one',
};

const mockBaseModel2: Model = {
  id: 'base-2',
  name: 'Base_Model_Two',
  createdAt: '2023-01-02T00:00:00Z',
  sourceUri: '/path/base2',
  createdBy: 'Base Author 2',
  onboardingStatus: ModelOnboardingStatus.READY,
  canonicalName: 'base-org/base-model-two',
};

const mockBaseModel3: Model = {
  id: 'base-3',
  name: 'Failed_Base_Model_Three',
  createdAt: '2023-01-02T00:00:00Z',
  sourceUri: '/path/base2',
  createdBy: 'Base Author 2',
  onboardingStatus: ModelOnboardingStatus.FAILED,
  canonicalName: 'base-org/base-model-three',
};

const mockBaseModel4: Model = {
  id: 'base-4',
  name: 'Pending_Base_Model_Four',
  createdAt: '2023-01-02T00:00:00Z',
  sourceUri: '/path/base2',
  createdBy: 'Base Author 4',
  onboardingStatus: ModelOnboardingStatus.PENDING,
  canonicalName: 'base-org/base-model-four',
};

// Recipe that uses 4 GPUs — drives the batch-size-must-be-a-multiple validation.
const mockGpuBaseModel: Model = {
  id: 'gpu-base',
  name: 'Gpu_Base_Model',
  createdAt: '2023-01-04T00:00:00Z',
  sourceUri: null,
  createdBy: 'GPU Author',
  onboardingStatus: ModelOnboardingStatus.READY,
  canonicalName: 'gpu-org/gpu-base-model',
};
const MOCK_GPU_COUNT = 4;

const mockFinetunedModel: AIMModel = {
  metadata: {
    name: 'wb-finetune-auto-generated-cr',
    creationTimestamp: '2023-01-03T00:00:00Z',
    labels: {
      [AIM_MODEL_WORKLOAD_ID_LABEL]: 'finetuned-1',
      [AIM_MODEL_NAME_LABEL]: 'Existing-Finetuned-Model',
    },
  },
  spec: {
    profiles: {
      overrides: {
        modelSources: [
          { modelId: 'finetune-org/existing-finetuned-model', sourceUri: '' },
        ],
      },
    },
  },
  status: { status: 'Ready' },
};

const mockFinetunedModelWithInvalidCharacters: Model = {
  id: 'finetuned-2',
  name: 'Finetuned Model With Invalid Characters !@#',
  createdAt: '2023-01-03T00:00:00Z',
  sourceUri: '/path/finetuned1',
  createdBy: 'Finetune Author',
  onboardingStatus: ModelOnboardingStatus.READY,
  canonicalName: 'finetune-org/finetuned-model-invalid',
};

const mockModels: Model[] = [
  mockBaseModel1,
  mockBaseModel2,
  mockBaseModel3,
  mockBaseModel4,
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

describe('FinetuneDrawer', () => {
  let onOpenChangeMock: ReturnType<typeof vi.fn<() => void>>;
  let onConfirmActionMock: ReturnType<
    typeof vi.fn<(param: { id: string; params: ModelFinetuneParams }) => void>
  >;
  let currentProjectSecrets: SecretResponseData[] = [];
  let mockQueryClient: {
    fetchQuery: ReturnType<typeof vi.fn>;
    invalidateQueries: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockToast.success.mockClear();
    mockToast.error.mockClear();
    onOpenChangeMock = vi.fn<() => void>();
    onConfirmActionMock =
      vi.fn<(param: { id: string; params: ModelFinetuneParams }) => void>();

    // Default project secrets data - HuggingFace token
    currentProjectSecrets = [
      {
        metadata: {
          name: 'hf-secret-1',
          namespace: 'project-1',
          uid: 'abc123',
          labels: undefined,
          annotations: undefined,
          creationTimestamp: new Date().toISOString(),
        },
        displayName: 'hf-secret-1',
        useCase: SecretUseCase.HUGGING_FACE,
      },
    ];

    // Mock createProjectSecret to return a successful response
    (createProjectSecret as Mock).mockResolvedValue({
      metadata: {
        name: 'new-secret-id',
        namespace: 'project-1',
        uid: 'new-secret-uid',
        createdAt: new Date().toISOString(),
      },
      displayName: 'new-secret-id',
      useCase: SecretUseCase.HUGGING_FACE,
    });

    // Mock fetchProjectSecrets to return current secrets
    (fetchProjectSecrets as Mock).mockImplementation(() =>
      Promise.resolve({ projectSecrets: currentProjectSecrets }),
    );

    // Configure mocks for listAllProjectFineTunedModels and listAllWorkloads
    vi.mocked(listAllProjectFineTunedModels).mockResolvedValue([]);
    vi.mocked(listAllWorkloads).mockResolvedValue([]);

    // Reset the useQueryClient mock with a fresh fetchQuery implementation
    // fetchQuery will execute the provided queryFn (listAllProjectFineTunedModels or listAllWorkloads)
    mockQueryClient = {
      fetchQuery: vi.fn(async ({ queryFn }) => {
        return queryFn();
      }),
      invalidateQueries: vi.fn(),
    };
    vi.mocked(useQueryClient).mockReturnValue(
      mockQueryClient as unknown as QueryClient,
    );

    // Mock useQuery return value for datasets, models, and secrets
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
        // For secrets, return the current secrets data
        // The component's queryFn calls fetchProjectSecrets and extracts response.projectSecrets
        return {
          data: currentProjectSecrets,
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
    props: Partial<React.ComponentProps<typeof FinetuneDrawer>>,
  ) => {
    const defaultProps: React.ComponentProps<typeof FinetuneDrawer> = {
      isOpen: true,
      onOpenChange: onOpenChangeMock,
      onConfirmAction: onConfirmActionMock,
      model: undefined,
      finetunableModels: [
        {
          canonicalName: mockBaseModel1.canonicalName,
          gpuCount: 0,
          compatibleAccelerators: [],
          compatibleAcceleratorNames: [],
          hfTokenRequired: true,
        },
        {
          canonicalName: mockBaseModel2.canonicalName,
          gpuCount: 0,
          compatibleAccelerators: [],
          compatibleAcceleratorNames: [],
          hfTokenRequired: false,
        },
        {
          // Multi-GPU recipe — keeps the batch-size tests exercising the
          // token-selection path.
          canonicalName: mockGpuBaseModel.canonicalName,
          gpuCount: MOCK_GPU_COUNT,
          compatibleAccelerators: [],
          compatibleAcceleratorNames: [],
          hfTokenRequired: true,
        },
      ],
    };
    return render(<FinetuneDrawer {...defaultProps} {...props} />, {
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
      screen.queryByText(
        mockFinetunedModel.spec.profiles!.overrides!.modelSources![0].modelId,
      ),
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

  it('should call onOpenChange when cancel button is clicked', () => {
    renderComponent({});
    const cancelButton = screen.getByText('list.actions.finetune.modal.cancel');
    fireEvent.click(cancelButton);
    expect(onConfirmActionMock).not.toHaveBeenCalled();
    expect(onOpenChangeMock).toHaveBeenCalledTimes(1);
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
    await act(async () => {
      fireEvent.click(
        await screen.findByTestId(`dataset-select-${mockDataset1.id}`),
      );
    });

    const nameInput = screen.getByLabelText(
      'list.actions.finetune.modal.modelName.label',
    );
    fireEvent.change(nameInput, { target: { value: 'New_Finetuned_Model' } });

    // Select existing HuggingFace token from dropdown
    const tokenSelect = await screen.findByRole('button', {
      name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
    });
    fireEvent.click(tokenSelect);

    const tokenOptions = await screen.findAllByText('hf-secret-1');
    await act(async () => {
      fireEvent.click(tokenOptions[1]);
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
        id: mockBaseModel1.canonicalName,
        params: {
          displayName: 'New_Finetuned_Model',
          datasetId: mockDataset1.id,
          epochs: undefined,
          learningRate: undefined,
          batchSize: undefined,
          hfTokenSecretName: 'hf-secret-1',
        },
      });
      expect(onOpenChangeMock).toHaveBeenCalledTimes(1);
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
    // First fetchQuery (models) returns the existing model; second (workloads) returns empty list.
    mockQueryClient.fetchQuery
      .mockResolvedValueOnce([mockFinetunedModel])
      .mockResolvedValueOnce([]);

    renderComponent({});

    const nameInput = screen.getByLabelText(
      'list.actions.finetune.modal.modelName.label',
    );

    // Type the display name stored in AIM_MODEL_NAME_LABEL (not the auto-generated K8s resource name)
    fireEvent.change(nameInput, {
      target: {
        value: mockFinetunedModel.metadata.labels![AIM_MODEL_NAME_LABEL],
      },
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

  it('should show validation error for name matching an in-progress job', async () => {
    // No completed model, but a running finetuning workload with the same displayName.
    mockQueryClient.fetchQuery
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([{ displayName: 'my-model', status: 'Running' }]);

    renderComponent({});

    const nameInput = screen.getByLabelText(
      'list.actions.finetune.modal.modelName.label',
    );

    fireEvent.change(nameInput, { target: { value: 'my-model' } });

    await waitFor(
      () => {
        expect(
          screen.getByText(
            'list.actions.finetune.modal.modelName.nonUniqueNameError',
          ),
        ).toBeInTheDocument();
      },
      { timeout: 1000 },
    );

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
    await act(async () => {
      fireEvent.click(
        await screen.findByTestId(`dataset-select-${mockDataset1.id}`),
      );
    });

    const modelNameInput = screen.getByLabelText(
      'list.actions.finetune.modal.modelName.label',
    );
    fireEvent.change(modelNameInput, { target: { value: 'Advanced_Model' } });

    const tokenSelect = await screen.findByRole('button', {
      name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
    });
    fireEvent.click(tokenSelect);

    const tokenOptions = await screen.findAllByText('hf-secret-1');
    await act(async () => {
      fireEvent.click(tokenOptions[1]);
    });

    fireEvent.click(
      screen.getByText(
        'list.actions.finetune.modal.advancedSettingsAccordion.title',
      ),
    );

    const batchSizeInput = await screen.findByLabelText(
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
        id: mockBaseModel1.canonicalName,
        params: {
          displayName: 'Advanced_Model',
          datasetId: mockDataset1.id,
          epochs: 5,
          learningRate: 0.5,
          batchSize: 16,
          hfTokenSecretName: 'hf-secret-1',
        },
      });
      expect(onOpenChangeMock).toHaveBeenCalledTimes(1);
    });
  });

  describe('batch size constrained by recipe GPU count', () => {
    const fillRequiredFieldsForGpuRecipe = async () => {
      const baseModelSelect = screen.getByTestId('baseModelSelect');
      fireEvent.click(baseModelSelect);
      fireEvent.click(
        await screen.findByTestId(
          `model-select-${mockGpuBaseModel.canonicalName}`,
        ),
      );

      const datasetSelect = screen.getByTestId('datasetSelect');
      fireEvent.click(datasetSelect);
      await act(async () => {
        fireEvent.click(
          await screen.findByTestId(`dataset-select-${mockDataset1.id}`),
        );
      });

      const nameInput = screen.getByLabelText(
        'list.actions.finetune.modal.modelName.label',
      );
      fireEvent.change(nameInput, { target: { value: 'Gpu_Aware_Model' } });

      const tokenSelect = await screen.findByRole('button', {
        name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
      });
      fireEvent.click(tokenSelect);
      const tokenOptions = await screen.findAllByText('hf-secret-1');
      await act(async () => {
        fireEvent.click(tokenOptions[1]);
      });
    };

    const openAdvancedSettings = async () => {
      fireEvent.click(
        screen.getByText(
          'list.actions.finetune.modal.advancedSettingsAccordion.title',
        ),
      );
      await screen.findByLabelText(
        'list.actions.finetune.modal.batchSize.label',
      );
    };

    it('leaves batch size empty when a multi-GPU recipe is selected and submits undefined when not provided', async () => {
      renderComponent({});
      await fillRequiredFieldsForGpuRecipe();
      await openAdvancedSettings();

      const batchSizeInput = screen.getByLabelText(
        'list.actions.finetune.modal.batchSize.label',
      );
      // Selecting a recipe should NOT auto-fill batch size; the user must
      // explicitly opt in to a value (which is then constrained to multiples
      // of the recipe's GPU count via the input's step/min attributes).
      expect(batchSizeInput).toHaveValue('');

      const confirmButton = screen.getByText(
        'list.actions.finetune.modal.confirm',
      );
      fireEvent.click(confirmButton);

      await waitFor(() => {
        expect(onConfirmActionMock).toHaveBeenCalledTimes(1);
        expect(onConfirmActionMock).toHaveBeenCalledWith({
          id: mockGpuBaseModel.canonicalName,
          params: expect.objectContaining({
            batchSize: undefined,
          }),
        });
      });
    });

    it('resets a previously entered batch size when the selected recipe changes', async () => {
      renderComponent({});
      // Pick a non-GPU recipe first and enter a batch size.
      const baseModelSelect = screen.getByTestId('baseModelSelect');
      fireEvent.click(baseModelSelect);
      fireEvent.click(
        await screen.findByTestId(
          `model-select-${mockBaseModel1.canonicalName}`,
        ),
      );
      await openAdvancedSettings();

      const batchSizeInput = screen.getByLabelText(
        'list.actions.finetune.modal.batchSize.label',
      );
      fireEvent.change(batchSizeInput, { target: { value: '12' } });
      fireEvent.blur(batchSizeInput);
      await waitFor(() => {
        expect(batchSizeInput).toHaveValue('12');
      });

      // Switch to the multi-GPU recipe — the previously entered value must
      // not silently carry over because it likely violates the new recipe's
      // multiple-of-gpuCount constraint.
      fireEvent.click(screen.getByTestId('baseModelSelect'));
      fireEvent.click(
        await screen.findByTestId(
          `model-select-${mockGpuBaseModel.canonicalName}`,
        ),
      );

      await waitFor(() => {
        expect(batchSizeInput).toHaveValue('');
      });
    });

    it('accepts a batch size that is a multiple of the recipe GPU count', async () => {
      renderComponent({});
      await fillRequiredFieldsForGpuRecipe();
      await openAdvancedSettings();

      const batchSizeInput = screen.getByLabelText(
        'list.actions.finetune.modal.batchSize.label',
      );
      // 8 is a multiple of 4
      fireEvent.change(batchSizeInput, { target: { value: '8' } });
      fireEvent.blur(batchSizeInput);

      await waitFor(() => {
        expect(batchSizeInput).toHaveValue('8');
      });

      const confirmButton = screen.getByText(
        'list.actions.finetune.modal.confirm',
      );
      fireEvent.click(confirmButton);

      await waitFor(() => {
        expect(onConfirmActionMock).toHaveBeenCalledTimes(1);
        expect(onConfirmActionMock).toHaveBeenCalledWith({
          id: mockGpuBaseModel.canonicalName,
          params: expect.objectContaining({
            batchSize: 8,
          }),
        });
      });
    });
  });

  it('should use model id when model with local weights is provided', async () => {
    renderComponent({ model: mockBaseModel1 });

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
    // and should NOT include hfTokenSecretName since model is available locally
    await waitFor(() => {
      expect(onConfirmActionMock).toHaveBeenCalledTimes(1);
      expect(onConfirmActionMock).toHaveBeenCalledWith({
        id: mockBaseModel1.id, // Should use model id when model prop is provided
        params: {
          displayName: 'Model_With_Prop',
          datasetId: mockDataset1.id,
          epochs: undefined,
          learningRate: undefined,
          batchSize: undefined,
          // No hfTokenSecretName since model is already available locally
        },
      });
      expect(onOpenChangeMock).toHaveBeenCalledTimes(1);
    });
  });

  it('should use workload id when both id and resourceName are provided', async () => {
    const fineTunedModelWithResourceName: Model = {
      ...mockBaseModel1,
      id: 'workload-uuid-123',
      resourceName: 'wb-finetune-cr-456',
      sourceUri: 's3://bucket/model-weights',
    };

    renderComponent({ model: fineTunedModelWithResourceName });

    const datasetSelect = screen.getByTestId('datasetSelect');
    fireEvent.click(datasetSelect);
    fireEvent.click(
      await screen.findByTestId(`dataset-select-${mockDataset1.id}`),
    );

    const nameInput = screen.getByLabelText(
      'list.actions.finetune.modal.modelName.label',
    );
    fireEvent.change(nameInput, {
      target: { value: 'Finetuned_From_Finetuned' },
    });

    const confirmButton = screen.getByText(
      'list.actions.finetune.modal.confirm',
    );
    fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(onConfirmActionMock).toHaveBeenCalledWith({
        id: 'workload-uuid-123',
        params: {
          displayName: 'Finetuned_From_Finetuned',
          datasetId: mockDataset1.id,
          epochs: undefined,
          learningRate: undefined,
          batchSize: undefined,
        },
      });
    });
  });

  it('should handle error during model name uniqueness check gracefully', async () => {
    // Override the fetchQuery to throw an error
    mockQueryClient.fetchQuery.mockRejectedValue(new Error('Network error'));

    const consoleErrorSpy = vi
      .spyOn(console, 'error')
      .mockImplementation(() => {});

    try {
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
    } finally {
      consoleErrorSpy.mockRestore();
    }
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

  it('should hide HF Token section until a gated base model is selected (model undefined)', async () => {
    renderComponent({ model: undefined });

    // No base model selected yet — gating is unknown, so the section stays hidden.
    expect(
      screen.queryByRole('button', {
        name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
      }),
    ).not.toBeInTheDocument();

    // Selecting a gated base model reveals the section.
    const baseModelSelect = screen.getByTestId('baseModelSelect');
    fireEvent.click(baseModelSelect);
    fireEvent.click(
      await screen.findByTestId(`model-select-${mockBaseModel1.canonicalName}`),
    );

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

  it('should keep HF Token section hidden for a non-gated base model (model undefined)', async () => {
    renderComponent({ model: undefined });

    // mockBaseModel2 is non-gated (hfTokenRequired: false).
    const baseModelSelect = screen.getByTestId('baseModelSelect');
    fireEvent.click(baseModelSelect);
    fireEvent.click(
      await screen.findByTestId(`model-select-${mockBaseModel2.canonicalName}`),
    );

    // Section must never appear for a non-gated model.
    await waitFor(() => {
      const selectButton = screen.getByRole('button', {
        name: /list\.actions\.finetune\.modal\.baseModel\.label/i,
      });
      expect(selectButton).toHaveTextContent(mockBaseModel2.canonicalName);
    });
    expect(
      screen.queryByRole('button', {
        name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
      }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText('huggingFaceTokenDrawer.title'),
    ).not.toBeInTheDocument();
  });

  it('should hide HF Token section when model has local weights', () => {
    renderComponent({ model: mockBaseModel1 });

    // HF Token section should NOT be visible when model has local weights (sourceUri)
    expect(
      screen.queryByRole('button', {
        name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
      }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText('huggingFaceTokenDrawer.title'),
    ).not.toBeInTheDocument();
  });

  it('should show HF Token section when a gated model prop has no local weights', async () => {
    // mockBaseModel1's canonical name matches a recipe with hfTokenRequired: true.
    const gatedModelWithoutWeights = {
      ...mockBaseModel1,
      sourceUri: null,
    };
    renderComponent({ model: gatedModelWithoutWeights });

    // HF Token section should be visible: recipe is gated and model has no local weights.
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

  it('should hide HF Token section when a non-gated model prop has no local weights', () => {
    // mockBaseModel2's canonical name matches a recipe with hfTokenRequired: false.
    const nonGatedModelWithoutWeights = {
      ...mockBaseModel2,
      sourceUri: null,
    };
    renderComponent({ model: nonGatedModelWithoutWeights });

    // Non-gated remote model: no token needed, section hidden.
    expect(
      screen.queryByRole('button', {
        name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
      }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText('huggingFaceTokenDrawer.title'),
    ).not.toBeInTheDocument();
  });

  it('should submit without HF Token for a non-gated base model (model undefined)', async () => {
    renderComponent({ model: undefined });

    // Select the non-gated base model.
    const baseModelSelect = screen.getByTestId('baseModelSelect');
    fireEvent.click(baseModelSelect);
    fireEvent.click(
      await screen.findByTestId(`model-select-${mockBaseModel2.canonicalName}`),
    );

    const datasetSelect = screen.getByTestId('datasetSelect');
    fireEvent.click(datasetSelect);
    fireEvent.click(
      await screen.findByTestId(`dataset-select-${mockDataset1.id}`),
    );

    await waitFor(() => {
      expect(
        screen.queryByRole('listbox', {
          name: /list.actions.finetune.modal.dataset.label/i,
        }),
      ).not.toBeInTheDocument();
    });

    const nameInput = screen.getByLabelText(
      'list.actions.finetune.modal.modelName.label',
    );
    fireEvent.change(nameInput, { target: { value: 'NonGated_Model' } });

    const confirmButton = screen.getByText(
      'list.actions.finetune.modal.confirm',
    );
    fireEvent.click(confirmButton);

    // Submits successfully with no hfTokenSecretName.
    await waitFor(() => {
      expect(onConfirmActionMock).toHaveBeenCalledTimes(1);
      expect(onConfirmActionMock).toHaveBeenCalledWith({
        id: mockBaseModel2.canonicalName,
        params: {
          displayName: 'NonGated_Model',
          datasetId: mockDataset1.id,
          epochs: undefined,
          learningRate: undefined,
          batchSize: undefined,
        },
      });
      expect(onOpenChangeMock).toHaveBeenCalledTimes(1);
    });
  });

  it('should require HF Token for a gated base model and submit with the selected token', async () => {
    renderComponent({ model: undefined });

    // Select the gated base model.
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

    await waitFor(() => {
      expect(
        screen.queryByRole('listbox', {
          name: /list.actions.finetune.modal.dataset.label/i,
        }),
      ).not.toBeInTheDocument();
    });

    const nameInput = screen.getByLabelText(
      'list.actions.finetune.modal.modelName.label',
    );
    fireEvent.change(nameInput, { target: { value: 'Gated_Model' } });

    const confirmButton = screen.getByText(
      'list.actions.finetune.modal.confirm',
    );

    // Submit without a token first — gating must block it.
    fireEvent.click(confirmButton);
    await waitFor(() => {
      expect(
        screen.getByText('list.actions.finetune.modal.title'),
      ).toBeInTheDocument();
    });
    expect(onConfirmActionMock).not.toHaveBeenCalled();

    // Select an existing token, then submit successfully.
    const tokenSelect = await screen.findByRole('button', {
      name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
    });
    fireEvent.click(tokenSelect);
    const tokenOptions = await screen.findAllByText('hf-secret-1');
    fireEvent.click(tokenOptions[1]);

    fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(onConfirmActionMock).toHaveBeenCalledTimes(1);
      expect(onConfirmActionMock).toHaveBeenCalledWith({
        id: mockBaseModel1.canonicalName,
        params: {
          displayName: 'Gated_Model',
          datasetId: mockDataset1.id,
          epochs: undefined,
          learningRate: undefined,
          batchSize: undefined,
          hfTokenSecretName: 'hf-secret-1',
        },
      });
      expect(onOpenChangeMock).toHaveBeenCalledTimes(1);
    });
  });

  it('should require HF Token when fine-tuning from a gated canonical name (model undefined)', async () => {
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

    // Validate that submission was prevented by form validation:
    // the modal should remain open and the confirm action should not have been called
    await waitFor(() => {
      expect(
        screen.getByText('list.actions.finetune.modal.title'),
      ).toBeInTheDocument();
    });
    expect(onConfirmActionMock).not.toHaveBeenCalled();
    expect(onOpenChangeMock).not.toHaveBeenCalledWith(false);
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
          displayName: 'Finetuned_From_Existing',
          datasetId: mockDataset1.id,
          epochs: undefined,
          learningRate: undefined,
          batchSize: undefined,
          // No hfTokenSecretName - not needed since model has local weights
        },
      });
    });
  });

  it('should hide HF Token and submit without a token when re-finetuning a non-gated finetuned source', async () => {
    // A re-finetuned source carries its own resolved hfTokenRequired flag. When
    // it is false (weights already in S3, no gating), the drawer must hide the
    // token selector and let the form submit without a token — forcing a token
    // here would be incorrect since the backend does not require one.
    const nonGatedFinetunedSource = {
      id: 'finetuned-source-1',
      name: 'Existing_Finetuned_Source',
      createdAt: '2023-01-03T00:00:00Z',
      sourceUri: '',
      createdBy: 'Finetune Author',
      onboardingStatus: ModelOnboardingStatus.READY,
      canonicalName: '',
      hfTokenRequired: false,
    } as Model;

    renderComponent({ model: nonGatedFinetunedSource });

    // Token selector must never appear for a non-gated source.
    expect(
      screen.queryByRole('button', {
        name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
      }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText('huggingFaceTokenDrawer.title'),
    ).not.toBeInTheDocument();

    const datasetSelect = screen.getByTestId('datasetSelect');
    fireEvent.click(datasetSelect);
    fireEvent.click(
      await screen.findByTestId(`dataset-select-${mockDataset1.id}`),
    );

    const nameInput = screen.getByLabelText(
      'list.actions.finetune.modal.modelName.label',
    );
    fireEvent.change(nameInput, { target: { value: 'Refinetuned_Model' } });

    const confirmButton = screen.getByText(
      'list.actions.finetune.modal.confirm',
    );
    fireEvent.click(confirmButton);

    // Submits successfully with no hfTokenSecretName and no error toast.
    await waitFor(() => {
      expect(onConfirmActionMock).toHaveBeenCalledTimes(1);
      expect(onConfirmActionMock).toHaveBeenCalledWith({
        id: 'finetuned-source-1',
        params: {
          displayName: 'Refinetuned_Model',
          datasetId: mockDataset1.id,
          epochs: undefined,
          learningRate: undefined,
          batchSize: undefined,
        },
      });
      expect(onOpenChangeMock).toHaveBeenCalledTimes(1);
    });
    expect(mockToast.error).not.toHaveBeenCalled();
  });

  it('should enforce HF Token without crashing when re-finetuning a gated finetuned source', async () => {
    // A re-finetuned source that requires a token (hfTokenRequired: true) shows
    // the selector. Submitting with no token must surface the no-token toast via
    // the crash guard — parsing the empty index and guarding the absent entry —
    // rather than dereferencing an undefined token and tearing down the page.
    const gatedFinetunedSource = {
      id: 'finetuned-source-2',
      name: 'Gated_Finetuned_Source',
      createdAt: '2023-01-03T00:00:00Z',
      sourceUri: '',
      createdBy: 'Finetune Author',
      onboardingStatus: ModelOnboardingStatus.READY,
      canonicalName: '',
      hfTokenRequired: true,
    } as Model;

    renderComponent({ model: gatedFinetunedSource });

    // Token selector must be visible for a gated source.
    expect(
      screen.getByRole('button', {
        name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
      }),
    ).toBeInTheDocument();

    const datasetSelect = screen.getByTestId('datasetSelect');
    fireEvent.click(datasetSelect);
    fireEvent.click(
      await screen.findByTestId(`dataset-select-${mockDataset1.id}`),
    );

    const nameInput = screen.getByLabelText(
      'list.actions.finetune.modal.modelName.label',
    );
    fireEvent.change(nameInput, { target: { value: 'Refinetuned_Model' } });

    const confirmButton = screen.getByText(
      'list.actions.finetune.modal.confirm',
    );
    fireEvent.click(confirmButton);

    // An empty token index must surface the no-token notification, not crash.
    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith(
        'huggingFaceTokenDrawer.notifications.noTokenSelected',
      );
    });
    expect(onConfirmActionMock).not.toHaveBeenCalled();
  });

  describe('HuggingFace Token Duplicate Validation', () => {
    it('should validate duplicate Kubernetes secret names when creating new token', async () => {
      // Set existing Kubernetes secret with name 'existing-hf-token'
      currentProjectSecrets = [
        {
          metadata: {
            name: 'existing-hf-token',
            namespace: 'project-1',
            uid: 'abc123',
            labels: undefined,
            annotations: undefined,
            creationTimestamp: new Date().toISOString(),
          },
          displayName: 'existing-hf-token',
          useCase: SecretUseCase.HUGGING_FACE,
        },
      ];

      renderComponent({ model: undefined });

      // Fill required fields
      const baseModelSelect = screen.getByTestId('baseModelSelect');
      fireEvent.click(baseModelSelect);
      fireEvent.click(
        await screen.findByTestId(
          `model-select-${mockBaseModel1.canonicalName}`,
        ),
      );

      const datasetSelect = screen.getByTestId('datasetSelect');
      fireEvent.click(datasetSelect);
      fireEvent.click(
        await screen.findByTestId(`dataset-select-${mockDataset1.id}`),
      );

      await waitFor(() => {
        expect(
          screen.queryByRole('listbox', {
            name: /list.actions.finetune.modal.dataset.label/i,
          }),
        ).not.toBeInTheDocument();
      });

      const nameInput = screen.getByLabelText(
        'list.actions.finetune.modal.modelName.label',
      );
      fireEvent.change(nameInput, { target: { value: 'Test_Model' } });

      // Note: Full validation testing would require exposing the HuggingFaceTokenSelector's
      // internal form fields. This test verifies the component renders with existing secrets.
      await waitFor(() => {
        expect(
          screen.getByRole('button', {
            name: /huggingFaceTokenDrawer.fields.selectToken.label/i,
          }),
        ).toBeInTheDocument();
      });
    });
  });
});
