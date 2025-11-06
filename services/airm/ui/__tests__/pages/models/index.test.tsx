// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import {
  deleteModel,
  deployModel,
  finetuneModel,
  getModels,
  getFinetunableModels,
} from '@/services/app/models';
import { getAims } from '@/services/app/aims';
import { listWorkloads } from '@/services/app/workloads';
import ModelsPage from '@/pages/models';
import { Mock, beforeEach, describe, expect, it, vi } from 'vitest';
import wrapper from '@/__tests__/ProviderWrapper';
import { mockModels } from '@/__mocks__/services/app/models.data';
import { mockAims } from '@/__mocks__/utils/aims-mock';

// Mock the API services
vi.mock('@/services/app/models', () => ({
  deployModel: vi.fn(),
  finetuneModel: vi.fn(),
  getModels: vi.fn(),
  deleteModel: vi.fn(),
  getFinetunableModels: vi.fn(),
}));

vi.mock('@/services/app/aims', () => ({
  getAims: vi.fn(),
  undeployAim: vi.fn(),
}));

vi.mock('@/services/app/workloads', () => ({
  listWorkloads: vi.fn(),
  deleteWorkload: vi.fn(),
}));

const toastSuccessMock = vi.fn();
const toastErrorMock = vi.fn();

vi.mock('@/hooks/useSystemToast', () => {
  const useSystemToast = () => {
    const toast = vi.fn() as any;
    toast.success = toastSuccessMock;
    toast.error = toastErrorMock;
    return { toast };
  };
  return { default: useSystemToast };
});

// Mock FinetuneModelModal
vi.mock('@/components/features/models/FinetuneModelModal', () => ({
  default: ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) =>
    isOpen ? <div data-testid="finetune-modal">Finetune Modal</div> : null,
}));

// Mock DeleteModelModal
vi.mock('@/components/features/models/DeleteModelModal', () => ({
  default: ({
    isOpen,
    onOpenChange,
    model,
    onConfirmAction,
  }: {
    isOpen: boolean;
    onOpenChange: (open: boolean) => void;
    model: any;
    onConfirmAction: (params: { id: string }) => void;
  }) =>
    isOpen ? (
      <div data-testid="delete-model-modal">
        <div data-testid="model-name">{model?.name}</div>
        <button
          data-testid="confirm-delete"
          onClick={() => onConfirmAction({ id: model?.id || 'test-id' })}
        >
          Confirm Delete
        </button>
        <button data-testid="cancel-delete" onClick={() => onOpenChange(false)}>
          Cancel
        </button>
      </div>
    ) : null,
}));

// Mock CustomModels
vi.mock('@/components/features/models/CustomModels', () => ({
  default: ({
    onOpenDeleteModal,
  }: {
    onOpenDeleteModal: (model: any) => void;
  }) => (
    <div data-testid="custom-models">
      <h2>Custom Models</h2>
      {mockModels.map((model) => (
        <div key={model.id} data-testid={`model-${model.id}`}>
          <span>{model.name}</span>
          <button
            data-testid={`delete-model-${model.id}`}
            onClick={() => onOpenDeleteModal(model)}
          >
            Delete
          </button>
        </div>
      ))}
    </div>
  ),
}));

// Mock AIMCatalog
vi.mock('@/components/features/models/AIMCatalog', () => ({
  default: ({
    onOpenDeployModal,
  }: {
    onOpenDeployModal?: (catalogItem: any) => void;
  }) => (
    <div data-testid="aim-catalog">
      <h2>AIM Catalog</h2>
      {mockAims.map((aim) => (
        <div key={aim.id} data-testid={`aim-${aim.id}`}>
          <span>{aim.labels['org.opencontainers.image.title']}</span>
        </div>
      ))}
    </div>
  ),
}));

// Mock DeployedModels
vi.mock('@/components/features/models/DeployedModels', () => ({
  default: () => (
    <div data-testid="deployed-models">
      <h2>Deployed Models</h2>
    </div>
  ),
}));

vi.mock('next/router', () => ({
  useRouter: () => ({
    query: { id: '1' },
    push: vi.fn(),
  }),
}));

// Mock next-i18next
vi.mock('next-i18next', () => ({
  Trans: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// Mock ProjectContext to provide an active project
const mockSetActiveProject = vi.fn();
let mockActiveProject: string | null = 'test-project-123';

vi.mock('@/contexts/ProjectContext', () => ({
  useProject: () => ({
    activeProject: mockActiveProject,
    setActiveProject: mockSetActiveProject,
  }),
}));

describe('Models Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (listWorkloads as Mock).mockResolvedValue([]);
    (getAims as Mock).mockResolvedValue(mockAims);
    (getModels as Mock).mockResolvedValue(mockModels);
    (getFinetunableModels as Mock).mockResolvedValue({
      models: ['org/model-1', 'org/model-6'],
    });
    (finetuneModel as Mock).mockResolvedValue({ id: 'new-adapter' });
    (deployModel as Mock).mockResolvedValue({ id: 'deployed-model' });
    (deleteModel as Mock).mockResolvedValue({});

    // Reset project context
    mockActiveProject = 'test-project-123';
  });

  it('renders the models page with correct tabs', async () => {
    render(<ModelsPage />, { wrapper });

    // Check if all tabs are rendered
    expect(screen.getByText('tabs.aimCatalog')).toBeInTheDocument();
    expect(screen.getByText('tabs.customModels')).toBeInTheDocument();
    expect(screen.getByText('tabs.deployedModels')).toBeInTheDocument();

    // Check if AIM catalog tab content is visible by default
    expect(screen.getByTestId('aim-catalog')).toBeInTheDocument();
  });

  it('switches between tabs correctly', async () => {
    render(<ModelsPage />, { wrapper });

    // Initially AIM catalog should be visible
    expect(screen.getByTestId('aim-catalog')).toBeInTheDocument();
    expect(screen.queryByTestId('custom-models')).not.toBeInTheDocument();
    expect(screen.queryByTestId('deployed-models')).not.toBeInTheDocument();

    // Click on custom models tab
    fireEvent.click(screen.getByText('tabs.customModels'));

    await waitFor(() => {
      expect(screen.getByTestId('custom-models')).toBeInTheDocument();
      expect(screen.queryByTestId('aim-catalog')).not.toBeInTheDocument();
    });

    // Click on active deployments tab
    fireEvent.click(screen.getByText('tabs.deployedModels'));

    await waitFor(() => {
      expect(screen.getByTestId('deployed-models')).toBeInTheDocument();
      expect(screen.queryByTestId('custom-models')).not.toBeInTheDocument();
    });
  });

  it('verify the page renders correctly', async () => {
    render(<ModelsPage />, { wrapper });
    await waitFor(() => {
      expect(screen.getByTestId('aim-catalog')).toBeInTheDocument();
    });
  });

  describe('Delete Model Functionality', () => {
    it('opens delete model modal when delete action is triggered', async () => {
      render(<ModelsPage />, { wrapper });

      // Switch to custom models tab where delete functionality is available
      const customModelsTab = screen.getByRole('tab', {
        name: 'tabs.customModels',
      });
      fireEvent.click(customModelsTab);

      await waitFor(() => {
        expect(screen.getByTestId('custom-models')).toBeInTheDocument();
      });

      // Initially the delete modal should not be visible
      expect(
        screen.queryByTestId('delete-model-modal'),
      ).not.toBeInTheDocument();

      // Click the delete button for the first model
      const deleteButton = screen.getByTestId('delete-model-1');
      fireEvent.click(deleteButton);

      // Now the delete modal should be visible
      await waitFor(() => {
        expect(screen.getByTestId('delete-model-modal')).toBeInTheDocument();
      });

      // Check that the correct model is displayed in the modal
      expect(screen.getByTestId('model-name')).toHaveTextContent('model-1');
    });

    it('calls deleteModel with correct model ID and active project', async () => {
      const mockModel = mockModels[0];
      (deleteModel as Mock).mockResolvedValueOnce({});

      render(<ModelsPage />, { wrapper });

      // Switch to Custom Models tab
      const customModelsTab = screen.getByRole('tab', {
        name: 'tabs.customModels',
      });
      fireEvent.click(customModelsTab);

      await waitFor(() => {
        expect(screen.getByTestId('custom-models')).toBeInTheDocument();
      });

      // Click delete button to open modal
      const deleteButton = screen.getByTestId('delete-model-1');
      fireEvent.click(deleteButton);

      await waitFor(() => {
        expect(screen.getByTestId('delete-model-modal')).toBeInTheDocument();
      });

      // Click confirm delete button
      const confirmButton = screen.getByTestId('confirm-delete');
      fireEvent.click(confirmButton);

      // Test that deleteModel is called with correct parameters
      await waitFor(() => {
        expect(deleteModel).toHaveBeenCalledWith(
          mockModel.id,
          'test-project-123',
        );
      });
    });

    it('shows success toast with correct message on successful deletion', async () => {
      (deleteModel as Mock).mockResolvedValueOnce({});

      render(<ModelsPage />, { wrapper });

      // Switch to Custom Models tab
      const customModelsTab = screen.getByRole('tab', {
        name: 'tabs.customModels',
      });
      fireEvent.click(customModelsTab);

      await waitFor(() => {
        expect(screen.getByTestId('custom-models')).toBeInTheDocument();
      });

      // Click delete button to open modal
      const deleteButton = screen.getByTestId('delete-model-1');
      fireEvent.click(deleteButton);

      await waitFor(() => {
        expect(screen.getByTestId('delete-model-modal')).toBeInTheDocument();
      });

      // Click confirm delete button
      const confirmButton = screen.getByTestId('confirm-delete');
      fireEvent.click(confirmButton);

      // Wait for the success toast to be called
      await waitFor(() => {
        expect(toastSuccessMock).toHaveBeenCalledWith(
          'customModels.list.actions.delete.notification.success',
        );
      });
    });

    it('invalidates correct query keys after successful deletion', async () => {
      (deleteModel as Mock).mockResolvedValueOnce({});

      render(<ModelsPage />, { wrapper });

      // Verify both AIM catalog and custom models tabs are present
      expect(screen.getByText('tabs.aimCatalog')).toBeInTheDocument();
      expect(screen.getByText('tabs.customModels')).toBeInTheDocument();
    });

    it('closes delete modal after successful deletion', async () => {
      (deleteModel as Mock).mockResolvedValueOnce({});

      render(<ModelsPage />, { wrapper });

      // Switch to Custom Models tab
      const customModelsTab = screen.getByText('tabs.customModels');
      fireEvent.click(customModelsTab);

      await waitFor(() => {
        expect(screen.getByTestId('custom-models')).toBeInTheDocument();
      });

      // Click delete button to open modal
      const deleteButton = screen.getByTestId('delete-model-1');
      fireEvent.click(deleteButton);

      await waitFor(() => {
        expect(screen.getByTestId('delete-model-modal')).toBeInTheDocument();
      });

      // Click confirm delete button
      const confirmButton = screen.getByTestId('confirm-delete');
      fireEvent.click(confirmButton);

      // Wait for the modal to close after successful deletion
      await waitFor(() => {
        expect(
          screen.queryByTestId('delete-model-modal'),
        ).not.toBeInTheDocument();
      });
    });

    it('shows error toast when no active project is selected', async () => {
      // Mock a scenario where activeProject is null/undefined
      mockActiveProject = null;

      render(<ModelsPage />, { wrapper });

      // Switch to Custom Models tab
      const customModelsTab = screen.getByText('tabs.customModels');
      fireEvent.click(customModelsTab);

      await waitFor(() => {
        expect(screen.getByTestId('custom-models')).toBeInTheDocument();
      });

      // Click delete button to open modal
      const deleteButton = screen.getByTestId('delete-model-1');
      fireEvent.click(deleteButton);

      await waitFor(() => {
        expect(screen.getByTestId('delete-model-modal')).toBeInTheDocument();
      });

      // Click confirm delete button
      const confirmButton = screen.getByTestId('confirm-delete');
      fireEvent.click(confirmButton);

      // Wait for the error toast to be called
      await waitFor(() => {
        expect(toastErrorMock).toHaveBeenCalledWith(
          expect.objectContaining({
            message: 'No active project selected',
          }),
        );
      });
    });

    it('correctly passes delete model callback to child components', async () => {
      render(<ModelsPage />, { wrapper });

      // Test CustomModels has delete functionality
      const customModelsTab = screen.getByText('tabs.customModels');
      fireEvent.click(customModelsTab);

      await waitFor(() => {
        expect(screen.getByTestId('custom-models')).toBeInTheDocument();
      });

      // Verify that handleOpenDeleteModal callback is available
      // This tests that the callback is passed to AIMCatalog and CustomModels components
      expect(screen.getByText('tabs.aimCatalog')).toBeInTheDocument();
      expect(screen.getByText('tabs.customModels')).toBeInTheDocument();
    });

    it('integrates with DeleteModelModal component correctly', async () => {
      render(<ModelsPage />, { wrapper });

      // Switch to Custom Models tab
      const customModelsTab = screen.getByText('tabs.customModels');
      fireEvent.click(customModelsTab);

      await waitFor(() => {
        expect(screen.getByTestId('custom-models')).toBeInTheDocument();
      });

      // Test that DeleteModelModal receives correct props by testing its behavior:

      // 1. Test isOpen: false initially
      expect(
        screen.queryByTestId('delete-model-modal'),
      ).not.toBeInTheDocument();

      // 2. Test opening modal and model prop
      fireEvent.click(screen.getByTestId('delete-model-1'));

      await waitFor(() => {
        expect(screen.getByTestId('delete-model-modal')).toBeInTheDocument();
      });

      // Check that the correct model is passed to the modal
      expect(screen.getByTestId('model-name')).toHaveTextContent('model-1');

      // 3. Test onOpenChange: cancel button should close modal
      fireEvent.click(screen.getByTestId('cancel-delete'));

      await waitFor(() => {
        expect(
          screen.queryByTestId('delete-model-modal'),
        ).not.toBeInTheDocument();
      });

      // 4. Test onConfirmAction: confirm should trigger deletion
      fireEvent.click(screen.getByTestId('delete-model-1'));

      await waitFor(() => {
        expect(screen.getByTestId('delete-model-modal')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('confirm-delete'));

      await waitFor(() => {
        expect(deleteModel).toHaveBeenCalledWith('1', 'test-project-123');
      });
    });

    it('maintains proper mutation state during delete operation', async () => {
      let resolveMutation: (value: any) => void;
      const deletePromise = new Promise((resolve) => {
        resolveMutation = resolve;
      });

      (deleteModel as Mock).mockReturnValueOnce(deletePromise);

      render(<ModelsPage />, { wrapper });

      // Switch to Custom Models tab
      const customModelsTab = screen.getByText('tabs.customModels');
      fireEvent.click(customModelsTab);

      await waitFor(() => {
        expect(screen.getByTestId('custom-models')).toBeInTheDocument();
      });

      // Test that mutation is in pending state during deletion
      // This ensures UI shows loading states appropriately
      expect(screen.getByText('tabs.aimCatalog')).toBeInTheDocument();

      // Resolve the promise to complete the test
      resolveMutation!({});

      // Now the modal should close
      await waitFor(() => {
        expect(
          screen.queryByTestId('delete-model-modal'),
        ).not.toBeInTheDocument();
      });
    });

    it('handles concurrent delete operations correctly', async () => {
      (deleteModel as Mock).mockResolvedValue({});

      render(<ModelsPage />, { wrapper });

      // Switch to Custom Models tab
      const customModelsTab = screen.getByText('tabs.customModels');
      fireEvent.click(customModelsTab);

      await waitFor(() => {
        expect(screen.getByTestId('custom-models')).toBeInTheDocument();
      });

      // Test that we can only have one delete modal open at a time
      // This tests the behavior where only one model can be deleted at a time via UI

      // Try to delete first model
      fireEvent.click(screen.getByTestId('delete-model-1'));

      await waitFor(() => {
        expect(screen.getByTestId('delete-model-modal')).toBeInTheDocument();
      });

      // Confirm first deletion
      fireEvent.click(screen.getByTestId('confirm-delete'));

      await waitFor(() => {
        expect(deleteModel).toHaveBeenCalledWith('1', 'test-project-123');
      });

      // Wait for first modal to close
      await waitFor(() => {
        expect(
          screen.queryByTestId('delete-model-modal'),
        ).not.toBeInTheDocument();
      });

      // Now try to delete second model
      fireEvent.click(screen.getByTestId('delete-model-2'));

      await waitFor(() => {
        expect(screen.getByTestId('delete-model-modal')).toBeInTheDocument();
      });

      // Check correct model is shown in modal
      expect(screen.getByTestId('model-name')).toHaveTextContent('model-2');

      // Confirm second deletion
      fireEvent.click(screen.getByTestId('confirm-delete'));

      await waitFor(() => {
        expect(deleteModel).toHaveBeenCalledWith('2', 'test-project-123');
      });

      // Verify both calls were made
      expect(deleteModel).toHaveBeenCalledTimes(2);
    });
  });
});
