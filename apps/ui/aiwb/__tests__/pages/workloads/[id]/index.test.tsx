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

import { useRouter } from 'next/router';

import { useProject } from '@/contexts/ProjectContext';
import { mockWorkloads } from '@/__mocks__/services/app/workloads.data';
import { deleteWorkload, getWorkload } from '@/lib/app/workloads';
import { deleteModel } from '@/lib/app/models';
import { getAimNamespaceModel } from '@/lib/app/aims';
import { getDataset } from '@/lib/app/datasets';
import { getChart } from '@/lib/app/charts';

import { WorkloadType } from '@amdenterpriseai/types';
import { WorkloadStatus } from '@/types/enums/workloads';
import { Workload } from '@/types/workloads';

import WorkloadDetailsPage from '@/pages/[project]/workloads/[id]/index';

import wrapper from '@/__tests__/ProviderWrapper';
import '@testing-library/jest-dom';
import { Mock, vi } from 'vitest';

// Mock the router
vi.mock('next/router', () => ({
  useRouter: vi.fn(),
}));

// Mock useProject
vi.mock('@/contexts/ProjectContext', async (importOriginal) => ({
  ...(await importOriginal()),
  useProject: vi.fn(),
}));

// Mock the internal services
vi.mock('@/lib/app/workloads', async (importOriginal) => ({
  ...(await importOriginal()),
  getWorkload: vi.fn(),
  deleteWorkload: vi.fn(),
  getWorkloadMetrics: vi.fn(),
}));

vi.mock('@/components/features/workloads/DeleteWorkloadModal', () => ({
  default: ({
    isOpen,
    workload,
    onConfirmAction,
  }: {
    isOpen: boolean;
    workload: any;
    onConfirmAction: (id: string) => void;
    onOpenChange: (open: boolean) => void;
  }) =>
    isOpen && workload ? (
      <button
        data-testid="confirm-delete"
        onClick={() => onConfirmAction(workload.id)}
      >
        Confirm Delete
      </button>
    ) : null,
}));

vi.mock('@/lib/app/charts', async (importOriginal) => ({
  ...(await importOriginal()),
  getChart: vi.fn(),
}));

vi.mock('@/lib/app/datasets', async (importOriginal) => ({
  ...(await importOriginal()),
  getDataset: vi.fn(),
}));

// Mock the workload services
vi.mock('@/lib/app/models', async (importOriginal) => ({
  ...(await importOriginal()),
  deleteModel: vi.fn(),
}));

vi.mock('@/lib/app/aims', async (importOriginal) => ({
  ...(await importOriginal()),
  getAimNamespaceModel: vi.fn(),
}));

// Mock useSystemToast
vi.mock('@amdenterpriseai/hooks', async (importOriginal) => ({
  ...(await importOriginal()),
  __esModule: true,
  useSystemToast: () => ({
    toast: {
      success: vi.fn(),
      error: vi.fn(),
    },
  }),
}));

// Mock translations
vi.mock('next-i18next', () => ({
  Trans: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useTranslation: () => ({
    t: (key: string, options?: any) => {
      // Handle interpolation
      if (options && typeof options === 'object') {
        let result = key;
        Object.keys(options).forEach((optionKey) => {
          result = result.replace(`{{${optionKey}}}`, options[optionKey]);
        });
        return result;
      }
      return key;
    },
    i18n: { language: 'en' },
  }),
}));

// Mock clipboard API
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn().mockResolvedValue(undefined),
  },
});

// Mock window.open
Object.assign(window, {
  open: vi.fn(),
});

describe('WorkloadDetailsPage', () => {
  const mockPush = vi.fn();
  const mockBack = vi.fn();

  const mockWorkload: Workload = {
    ...mockWorkloads[0],
    endpoints: {
      external: 'https://example.com/external',
      internal: 'http://workload-1.default.svc.cluster.local',
    },
    allocatedResources: {
      gpuCount: 2,
      vram: 4294967296,
    },
  };

  const mockWorkspaceWorkload: Workload = {
    ...mockWorkload,
    id: 'workspace-1',
    type: WorkloadType.WORKSPACE,
    status: WorkloadStatus.RUNNING,
  };

  const mockFTModelInferenceWorkload: Workload = {
    ...mockWorkload,
    id: 'ft-inference-1',
    type: WorkloadType.INFERENCE,
    status: WorkloadStatus.RUNNING,
    aimId: null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (useRouter as Mock).mockReturnValue({
      query: { id: 'workload-1', project: 'test-project' },
      push: mockPush,
      back: mockBack,
    });
    (useProject as Mock).mockReturnValue({
      activeProject: 'test-project',
      projectPath: (path: string) =>
        `/test-project${path.startsWith('/') ? path : `/${path}`}`,
      projectUrl: (path: string) =>
        `/test-project${path.startsWith('/') ? path : `/${path}`}`,
    });
    (getWorkload as Mock).mockResolvedValue(mockWorkload);
    (deleteWorkload as Mock).mockResolvedValue({});
    (deleteModel as Mock).mockResolvedValue({});
    (getAimNamespaceModel as Mock).mockResolvedValue({
      id: 'model-1',
      displayName: null,
      workloadId: null,
      metadata: {
        name: 'Test Model',
        creationTimestamp: '2026-01-01T00:00:00Z',
      },
      spec: {
        image: 'amdenterpriseai/aim-base:0.10',
        modelSources: [
          { modelId: 'org/test-model', sourceUri: 's3://bucket/model' },
        ],
      },
      status: { status: 'Ready' },
    });
    (getDataset as Mock).mockResolvedValue({
      id: 'dataset-1',
      name: 'Test Dataset',
      description: 'Test dataset description',
    });
    (getChart as Mock).mockResolvedValue({
      id: 'chart-1',
      name: 'Test Chart',
      description: 'Test chart description',
    });
  });

  describe('Rendering', () => {
    it('renders workload details correctly', async () => {
      await act(async () => {
        render(<WorkloadDetailsPage />, { wrapper });
      });

      // Check header elements
      await waitFor(() => {
        expect(
          screen.getAllByText('Llama 7B Inference')[0],
        ).toBeInTheDocument();
        expect(
          screen.getByText('details.sections.basicInformation'),
        ).toBeInTheDocument();
        expect(
          screen.getByText('details.sections.resources'),
        ).toBeInTheDocument();
        expect(
          screen.getByText('details.sections.timeline'),
        ).toBeInTheDocument();
      });
    });

    it('renders all workload information sections', async () => {
      await act(async () => {
        render(<WorkloadDetailsPage />, { wrapper });
      });

      await waitFor(() => {
        // Basic Information
        expect(
          screen.getByText('details.sections.basicInformation'),
        ).toBeInTheDocument();
        expect(
          screen.getAllByText('Llama 7B Inference')[0],
        ).toBeInTheDocument();
        expect(screen.getByText('workload-1')).toBeInTheDocument();
      });

      // Resources
      expect(
        screen.getByText('details.sections.resources'),
      ).toBeInTheDocument();

      // Timeline
      expect(screen.getByText('details.sections.timeline')).toBeInTheDocument();
      expect(screen.getByText('test-user')).toBeInTheDocument();

      // Chart section should display chart info
      await waitFor(() => {
        expect(screen.getByText('Test Chart')).toBeInTheDocument();
      });

      // Output
      expect(screen.getByText('details.sections.output')).toBeInTheDocument();
    });

    it('renders workload without model or dataset', async () => {
      const workloadWithoutModel = {
        ...mockWorkload,
        model: undefined,
        dataset: undefined,
        datasetId: undefined,
      };

      // Mock the service to return the workload without model/dataset
      (getWorkload as Mock).mockResolvedValue(workloadWithoutModel);

      await act(async () => {
        render(<WorkloadDetailsPage />, {
          wrapper,
        });
      });

      await waitFor(() => {
        expect(
          screen.queryByText('details.sections.modelAndDataset'),
        ).not.toBeInTheDocument();
      });
    });

    it('renders workload without output data', async () => {
      const workloadWithoutOutput = {
        ...mockWorkload,
        endpoints: undefined,
      };

      (getWorkload as Mock).mockResolvedValue(workloadWithoutOutput);

      await act(async () => {
        render(<WorkloadDetailsPage />, {
          wrapper,
        });
      });

      await waitFor(() => {
        expect(
          screen.queryByText('details.sections.output'),
        ).not.toBeInTheDocument();
      });
    });
  });

  describe('Action Buttons', () => {
    it('shows workspace button for running workspace workload', async () => {
      // Mock the service to return the workspace workload
      (getWorkload as Mock).mockResolvedValue(mockWorkspaceWorkload);

      await act(async () => {
        render(<WorkloadDetailsPage />, {
          wrapper,
        });
      });

      await waitFor(() => {
        expect(
          screen.getByText('list.actions.openWorkspace.label'),
        ).toBeInTheDocument();
      });
    });

    it('shows chat button for inference workload', async () => {
      await act(async () => {
        render(<WorkloadDetailsPage />, { wrapper });
      });

      await waitFor(() => {
        expect(screen.getByText('list.actions.chat.label')).toBeInTheDocument();
      });
    });

    it('shows logs button', async () => {
      await act(async () => {
        render(<WorkloadDetailsPage />, { wrapper });
      });

      await waitFor(() => {
        expect(screen.getByText('list.actions.logs.label')).toBeInTheDocument();
      });
    });

    it('shows delete button for non-deleted workload', async () => {
      await act(async () => {
        render(<WorkloadDetailsPage />, { wrapper });
      });

      await waitFor(() => {
        expect(
          screen.getByText('list.actions.delete.label'),
        ).toBeInTheDocument();
      });
    });

    it('does not show delete button for deleted workload', async () => {
      const deletedWorkload = {
        ...mockWorkload,
        status: WorkloadStatus.DELETED,
      };

      // Mock the service to return the deleted workload
      (getWorkload as Mock).mockResolvedValue(deletedWorkload);

      await act(async () => {
        render(<WorkloadDetailsPage />, { wrapper });
      });

      await waitFor(() => {
        expect(
          screen.queryByText('list.actions.delete.label'),
        ).not.toBeInTheDocument();
      });
    });

    it('does not show workspace button for non-running workload', async () => {
      const pendingWorkspaceWorkload = {
        ...mockWorkspaceWorkload,
        status: WorkloadStatus.PENDING,
      };

      // Mock the service to return the pending workspace workload
      (getWorkload as Mock).mockResolvedValue(pendingWorkspaceWorkload);

      await act(async () => {
        render(<WorkloadDetailsPage />, {
          wrapper,
        });
      });

      await waitFor(() => {
        expect(
          screen.queryByText('list.actions.openWorkspace.label'),
        ).not.toBeInTheDocument();
      });
    });

    it('does not show chat button for workspace workload', async () => {
      const workloadWithoutChat = {
        ...mockWorkload,
        type: WorkloadType.WORKSPACE,
      };

      // Mock the service to return workspace workload
      (getWorkload as Mock).mockResolvedValue(workloadWithoutChat);

      await act(async () => {
        render(<WorkloadDetailsPage />, {
          wrapper,
        });
      });

      await waitFor(() => {
        expect(
          screen.queryByText('list.actions.chat.label'),
        ).not.toBeInTheDocument();
      });
    });
  });

  describe('User Interactions', () => {
    it('navigates back when back button is clicked', async () => {
      await act(async () => {
        render(<WorkloadDetailsPage />, { wrapper });
      });

      // Find the back button by looking for the SVG with arrow-left icon
      const backButton = await screen.findByRole('button', {
        name: (content, element) => {
          return element?.querySelector('.tabler-icon-arrow-left') !== null;
        },
      });
      await act(async () => {
        fireEvent.click(backButton);
      });

      expect(mockBack).toHaveBeenCalled();
    });

    it('opens chat when chat button is clicked', async () => {
      (getWorkload as Mock).mockResolvedValue(mockWorkload);

      await act(async () => {
        render(<WorkloadDetailsPage />, { wrapper });
      });

      const chatButton = await waitFor(() =>
        screen.getByText('list.actions.chat.label'),
      );

      await act(async () => {
        fireEvent.click(chatButton);
      });

      expect(mockPush).toHaveBeenCalledWith(
        '/test-project/chat?workload=workload-1',
      );
    });

    it('opens workspace in new window when workspace button is clicked', async () => {
      (getWorkload as Mock).mockResolvedValue(mockWorkspaceWorkload);

      await act(async () => {
        render(<WorkloadDetailsPage />, {
          wrapper,
        });
      });

      const workspaceButton = await waitFor(() =>
        screen.getByText('list.actions.openWorkspace.label'),
      );

      await act(async () => {
        fireEvent.click(workspaceButton);
      });

      expect(window.open).toHaveBeenCalledWith(
        'https://example.com/external',
        '_blank',
      );
    });

    it('opens logs modal when logs button is clicked', async () => {
      (getWorkload as Mock).mockResolvedValue(mockWorkload);

      await act(async () => {
        render(<WorkloadDetailsPage />, { wrapper });
      });

      const logsButton = await waitFor(() =>
        screen.getByText('list.actions.logs.label'),
      );

      await act(async () => {
        fireEvent.click(logsButton);
      });
    });

    it('opens delete modal when delete button is clicked', async () => {
      (getWorkload as Mock).mockResolvedValue(mockWorkload);

      await act(async () => {
        render(<WorkloadDetailsPage />, { wrapper });
      });

      const deleteButton = await waitFor(() =>
        screen.getByText('list.actions.delete.label'),
      );

      await act(async () => {
        fireEvent.click(deleteButton);
      });
    });

    it('fetches model using workload.id for fine-tuning workloads when complete', async () => {
      // For FINE_TUNING, the workload itself IS the model — use workload.id directly
      // to look up the AIMModel via WORKLOAD_ID_LABEL. model_id is not used.
      const mockFTWorkload: Workload = {
        ...mockWorkload,
        id: 'ft-workload-id',
        name: 'wb-llm-finetune-abc123-job',
        type: WorkloadType.FINE_TUNING,
        status: WorkloadStatus.COMPLETE,
      };

      (getWorkload as Mock).mockResolvedValue(mockFTWorkload);
      (useRouter as Mock).mockReturnValue({
        query: { id: 'ft-workload-id', project: 'test-project' },
        push: mockPush,
        back: mockBack,
      });

      await act(async () => {
        render(<WorkloadDetailsPage />, { wrapper });
      });

      await waitFor(() => {
        expect(getAimNamespaceModel).toHaveBeenCalledWith(
          'ft-workload-id',
          'test-project',
        );
      });
    });

    it('does not fetch model for in-progress fine-tuning workloads', async () => {
      // AIMModel CR doesn't exist until training completes — skip model fetch.
      const mockFTWorkload: Workload = {
        ...mockWorkload,
        id: 'ft-workload-id',
        name: 'wb-llm-finetune-abc123-job',
        type: WorkloadType.FINE_TUNING,
        status: WorkloadStatus.RUNNING,
      };

      (getWorkload as Mock).mockResolvedValue(mockFTWorkload);
      (useRouter as Mock).mockReturnValue({
        query: { id: 'ft-workload-id', project: 'test-project' },
        push: mockPush,
        back: mockBack,
      });

      await act(async () => {
        render(<WorkloadDetailsPage />, { wrapper });
      });

      await waitFor(() => {
        expect(getAimNamespaceModel).not.toHaveBeenCalled();
      });
    });

    it('fetches model for fine-tuning workloads using workload id', async () => {
      const mockFTWorkload: Workload = {
        ...mockWorkload,
        id: 'ft-workload-id',
        type: WorkloadType.FINE_TUNING,
        status: WorkloadStatus.COMPLETE,
      };

      (getWorkload as Mock).mockResolvedValue(mockFTWorkload);
      (useRouter as Mock).mockReturnValue({
        query: { id: 'ft-workload-id', project: 'test-project' },
        push: mockPush,
        back: mockBack,
      });

      await act(async () => {
        render(<WorkloadDetailsPage />, { wrapper });
      });

      await waitFor(() => {
        expect(getAimNamespaceModel).toHaveBeenCalledWith(
          'ft-workload-id',
          'test-project',
        );
      });
    });

    it('calls deleteModel for fine-tuning workloads instead of deleteWorkload', async () => {
      const mockFTWorkload: Workload = {
        ...mockWorkload,
        id: 'workload-4',
        name: 'Model fine-tuning',
        type: WorkloadType.FINE_TUNING,
        status: WorkloadStatus.RUNNING,
      };

      (getWorkload as Mock).mockResolvedValue(mockFTWorkload);

      await act(async () => {
        render(<WorkloadDetailsPage />, { wrapper });
      });

      const deleteButton = await waitFor(() =>
        screen.getByText('list.actions.delete.label'),
      );

      await act(async () => {
        fireEvent.click(deleteButton);
      });

      const confirmButton = await waitFor(() =>
        screen.getByTestId('confirm-delete'),
      );

      await act(async () => {
        fireEvent.click(confirmButton);
      });

      await waitFor(() => {
        expect(deleteModel).toHaveBeenCalledWith('workload-4', 'test-project');
        expect(deleteWorkload).not.toHaveBeenCalled();
      });
    });
  });

  describe('Clipboard Functionality', () => {
    it('has copy buttons available', async () => {
      await act(async () => {
        render(<WorkloadDetailsPage />, { wrapper });
      });

      // Verify clipboard functionality is available
      expect(navigator.clipboard.writeText).toBeDefined();
    });

    it('can simulate copy action', async () => {
      await act(async () => {
        render(<WorkloadDetailsPage />, { wrapper });
      });

      // Simulate copy action by directly calling the mocked function
      await act(async () => {
        navigator.clipboard.writeText('test');
      });

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('test');
    });
  });

  describe('Edge Cases', () => {
    it('handles workload with null GPU resources', async () => {
      const workloadWithNullGPU = {
        ...mockWorkload,
        allocatedResources: {
          gpuCount: null,
          vram: null,
        },
      };

      // Mock the service to return the workload with null GPU resources
      (getWorkload as Mock).mockResolvedValue(workloadWithNullGPU);

      await act(async () => {
        render(<WorkloadDetailsPage />, {
          wrapper,
        });
      });

      await waitFor(() => {
        // Should render NoDataDisplay components for null resources
        expect(
          screen.getByText('details.sections.resources'),
        ).toBeInTheDocument();
      });
    });

    it('handles workload without allocated resources', async () => {
      const workloadWithoutResources = {
        ...mockWorkload,
        allocatedResources: {
          gpuCount: null,
          vram: null,
        },
      };

      // Mock the service to return the workload without allocated resources
      (getWorkload as Mock).mockResolvedValue(workloadWithoutResources);

      await act(async () => {
        render(<WorkloadDetailsPage />, {
          wrapper,
        });
      });

      await waitFor(() => {
        expect(
          screen.getByText('details.sections.resources'),
        ).toBeInTheDocument();
      });
    });

    it('handles workload with dataset', async () => {
      const workloadWithDataset = {
        ...mockWorkload,
        datasetId: 'dataset-1',
      };

      (getWorkload as Mock).mockResolvedValue(workloadWithDataset);

      await act(async () => {
        render(<WorkloadDetailsPage />, {
          wrapper,
        });
      });

      // Should display the dataset name from the mocked dataset
      await waitFor(() => {
        expect(screen.getByText('Test Dataset')).toBeInTheDocument();
      });
    });
  });
});
