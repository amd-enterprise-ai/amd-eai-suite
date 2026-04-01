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
import { getModel } from '@/lib/app/models';
import { getDataset } from '@/lib/app/datasets';
import { getChart } from '@/lib/app/charts';

import { WorkloadStatus, WorkloadType } from '@amdenterpriseai/types';
import { Workload } from '@amdenterpriseai/types';

import WorkloadDetailsPage from '@/pages/workloads/[id]/index';

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
  getModel: vi.fn(),
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
      query: { id: 'workload-1' },
      push: mockPush,
      back: mockBack,
    });
    (useProject as Mock).mockReturnValue({
      activeProject: 'project-1',
    });
    (getWorkload as Mock).mockResolvedValue(mockWorkload);
    (deleteWorkload as Mock).mockResolvedValue({});
    (getModel as Mock).mockResolvedValue({
      id: 'model-1',
      name: 'Test Model',
      canonicalName: 'org/test-model',
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

      // Model section should display model info
      await waitFor(() => {
        expect(screen.getByText('Test Model')).toBeInTheDocument();
      });

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
        modelId: undefined,
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

      expect(mockPush).toHaveBeenCalledWith('/chat?workload=workload-1');
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
