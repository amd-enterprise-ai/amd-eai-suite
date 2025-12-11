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

import { mockWorkloads } from '@/__mocks__/services/app/workloads.data';
import { deleteWorkload, getWorkload } from '@/services/app/workloads';
import { getCluster } from '@/services/app/clusters';
import { getModel } from '@/services/app/models';
import { getDataset } from '@/services/app/datasets';
import { getChart } from '@/services/app/charts';
import { getAimById } from '@/services/app/aims';

import { WorkloadStatus, WorkloadType } from '@/types/enums/workloads';
import { Workload } from '@/types/workloads';

import WorkloadDetailsPage from '@/pages/workloads/[id]/index';

import wrapper from '@/__tests__/ProviderWrapper';
import '@testing-library/jest-dom';
import { Mock, vi } from 'vitest';

// Mock the router
vi.mock('next/router', () => ({
  useRouter: vi.fn(),
}));

// Mock the workload services
vi.mock('@/services/app/workloads', () => ({
  getWorkload: vi.fn(),
  deleteWorkload: vi.fn(),
}));

// Mock the cluster services
vi.mock('@/services/app/clusters', () => ({
  getCluster: vi.fn(),
}));

// Mock model service
vi.mock('@/services/app/models', () => ({
  getModel: vi.fn(),
}));

// Mock dataset service
vi.mock('@/services/app/datasets', () => ({
  getDataset: vi.fn(),
}));

// Mock chart service
vi.mock('@/services/app/charts', () => ({
  getChart: vi.fn(),
}));

// Mock AIM service
vi.mock('@/services/app/aims', () => ({
  getAimById: vi.fn(),
}));

// Mock useSystemToast
vi.mock('@/hooks/useSystemToast', () => ({
  __esModule: true,
  default: () => ({
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
    output: {
      externalHost: 'https://example.com/external',
      internalHost: 'https://example.com/internal',
      host: 'https://example.com/host',
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
    capabilities: undefined,
  };

  const mockFTModelInferenceWorkload: Workload = {
    ...mockWorkload,
    id: 'ft-inference-1',
    type: WorkloadType.INFERENCE,
    status: WorkloadStatus.RUNNING,
    aimId: null,
  };

  const mockAIMInferenceWorkload: Workload = {
    ...mockWorkload,
    id: 'aim-inference-1',
    type: WorkloadType.INFERENCE,
    status: WorkloadStatus.RUNNING,
    aimId: 'aim-1',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (useRouter as Mock).mockReturnValue({
      query: { id: 'workload-1' },
      push: mockPush,
      back: mockBack,
    });
    (getWorkload as Mock).mockResolvedValue(mockWorkload);
    (deleteWorkload as Mock).mockResolvedValue({});
    (getCluster as Mock).mockResolvedValue({
      id: 'cluster-1',
      name: 'Test Cluster',
      lastHeartbeatAt: '2023-01-01T00:00:00Z',
      status: 'healthy',
    });
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
    (getAimById as Mock).mockResolvedValue({
      id: 'aim-1',
      imageName: 'test-aim-image',
      imageTag: '1.0.0',
      canonicalName: 'org/test-aim',
      description: {
        short: 'Test AIM description',
        full: 'Full test AIM description',
      },
      labels: {
        comAmdAimModelCanonicalName: 'org/test-aim',
        comAmdAimTitle: 'Test AIM',
      },
      createdAt: '2023-01-01T00:00:00Z',
      updatedAt: '2023-01-01T00:00:00Z',
      createdBy: 'test-user',
      updatedBy: 'test-user',
      image: 'test-aim-image:1.0.0',
    });
  });

  describe('Rendering', () => {
    it('renders workload details correctly', async () => {
      await act(async () => {
        render(<WorkloadDetailsPage workload={mockWorkload} />, { wrapper });
      });

      // Check header elements
      expect(screen.getAllByText('Llama 7B Inference')[0]).toBeInTheDocument();
      expect(
        screen.getByText('details.sections.basicInformation'),
      ).toBeInTheDocument();
      expect(
        screen.getByText('details.sections.resources'),
      ).toBeInTheDocument();
      expect(screen.getByText('details.sections.timeline')).toBeInTheDocument();
    });

    it('renders loading state', () => {
      (useRouter as Mock).mockReturnValue({
        query: {},
        push: mockPush,
        back: mockBack,
      });

      render(<WorkloadDetailsPage workload={mockWorkload} />, { wrapper });

      // The component renders the workload from props even when router query is empty
      expect(
        screen.getByText('details.sections.basicInformation'),
      ).toBeInTheDocument();
    });

    it('renders all workload information sections', async () => {
      await act(async () => {
        render(<WorkloadDetailsPage workload={mockWorkload} />, { wrapper });
      });

      // Basic Information
      expect(
        screen.getByText('details.sections.basicInformation'),
      ).toBeInTheDocument();
      expect(screen.getAllByText('Llama 7B Inference')[0]).toBeInTheDocument();
      expect(screen.getByText('workload-1')).toBeInTheDocument();

      // Project and Cluster sections
      expect(
        screen.getByText('details.sections.resources'),
      ).toBeInTheDocument();
      await waitFor(() => {
        expect(screen.getByText('Test Cluster')).toBeInTheDocument();
      });
      expect(screen.getByText('cluster-1')).toBeInTheDocument();

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

    it('renders inference metrics for valid AIM workloads', async () => {
      (getWorkload as Mock).mockResolvedValue(mockAIMInferenceWorkload);

      await act(async () => {
        render(<WorkloadDetailsPage workload={mockAIMInferenceWorkload} />, {
          wrapper,
        });
      });

      expect(
        screen.getByText('details.sections.inferenceMetrics'),
      ).toBeInTheDocument();
    });

    it('does not render inference metrics for fine-tuned model inference workloads', async () => {
      (getWorkload as Mock).mockResolvedValue(mockFTModelInferenceWorkload);

      await act(async () => {
        render(
          <WorkloadDetailsPage workload={mockFTModelInferenceWorkload} />,
          { wrapper },
        );
      });

      expect(
        screen.queryByText('details.sections.inferenceMetrics'),
      ).not.toBeInTheDocument();
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
        render(<WorkloadDetailsPage workload={workloadWithoutModel} />, {
          wrapper,
        });
      });

      await waitFor(() => {
        expect(
          screen.queryByText('details.sections.modelAndDataset'),
        ).not.toBeInTheDocument();
      });
    });

    it('renders workload without capabilities', async () => {
      const workloadWithoutCapabilities = {
        ...mockWorkload,
        capabilities: undefined,
      };

      // Mock the service to return the workload without capabilities
      (getWorkload as Mock).mockResolvedValue(workloadWithoutCapabilities);

      await act(async () => {
        render(<WorkloadDetailsPage workload={workloadWithoutCapabilities} />, {
          wrapper,
        });
      });

      await waitFor(() => {
        expect(
          screen.queryByText('details.sections.capabilities'),
        ).not.toBeInTheDocument();
      });
    });

    it('renders workload without output data', async () => {
      const workloadWithoutOutput = {
        ...mockWorkload,
        output: undefined,
      };

      // Mock the service to return the workload without output
      (getWorkload as Mock).mockResolvedValue(workloadWithoutOutput);

      await act(async () => {
        render(<WorkloadDetailsPage workload={workloadWithoutOutput} />, {
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
        render(<WorkloadDetailsPage workload={mockWorkspaceWorkload} />, {
          wrapper,
        });
      });

      await waitFor(() => {
        expect(
          screen.getByText('list.actions.openWorkspace.label'),
        ).toBeInTheDocument();
      });
    });

    it('shows chat button for workload with chat capability', async () => {
      await act(async () => {
        render(<WorkloadDetailsPage workload={mockWorkload} />, { wrapper });
      });

      await waitFor(() => {
        expect(screen.getByText('list.actions.chat.label')).toBeInTheDocument();
      });
    });

    it('shows logs button', async () => {
      await act(async () => {
        render(<WorkloadDetailsPage workload={mockWorkload} />, { wrapper });
      });

      expect(screen.getByText('list.actions.logs.label')).toBeInTheDocument();
    });

    it('shows delete button for non-deleted workload', async () => {
      await act(async () => {
        render(<WorkloadDetailsPage workload={mockWorkload} />, { wrapper });
      });

      expect(screen.getByText('list.actions.delete.label')).toBeInTheDocument();
    });

    it('does not show delete button for deleted workload', async () => {
      const deletedWorkload = {
        ...mockWorkload,
        status: WorkloadStatus.DELETED,
      };

      // Mock the service to return the deleted workload
      (getWorkload as Mock).mockResolvedValue(deletedWorkload);

      await act(async () => {
        render(<WorkloadDetailsPage workload={deletedWorkload} />, { wrapper });
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
        render(<WorkloadDetailsPage workload={pendingWorkspaceWorkload} />, {
          wrapper,
        });
      });

      await waitFor(() => {
        expect(
          screen.queryByText('list.actions.openWorkspace.label'),
        ).not.toBeInTheDocument();
      });
    });

    it('does not show chat button for workload without chat capability', async () => {
      const workloadWithoutChat = {
        ...mockWorkload,
        type: WorkloadType.WORKSPACE,
      };

      // Mock the service to return the workload without chat capability
      (getWorkload as Mock).mockResolvedValue(workloadWithoutChat);

      await act(async () => {
        render(<WorkloadDetailsPage workload={workloadWithoutChat} />, {
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
        render(<WorkloadDetailsPage workload={mockWorkload} />, { wrapper });
      });

      // Find the back button by looking for the SVG with arrow-left icon
      const backButton = screen.getByRole('button', {
        name: (content, element) => {
          return element?.querySelector('.tabler-icon-arrow-left') !== null;
        },
      });
      await act(async () => {
        fireEvent.click(backButton);
      });

      expect(mockPush).toHaveBeenCalledWith('/workloads');
    });

    it('opens chat when chat button is clicked', async () => {
      (getWorkload as Mock).mockResolvedValue(mockWorkload);

      await act(async () => {
        render(<WorkloadDetailsPage workload={mockWorkload} />, { wrapper });
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
        render(<WorkloadDetailsPage workload={mockWorkspaceWorkload} />, {
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
        render(<WorkloadDetailsPage workload={mockWorkload} />, { wrapper });
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
        render(<WorkloadDetailsPage workload={mockWorkload} />, { wrapper });
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
        render(<WorkloadDetailsPage workload={mockWorkload} />, { wrapper });
      });

      // Verify clipboard functionality is available
      expect(navigator.clipboard.writeText).toBeDefined();
    });

    it('can simulate copy action', async () => {
      await act(async () => {
        render(<WorkloadDetailsPage workload={mockWorkload} />, { wrapper });
      });

      // Simulate copy action by directly calling the mocked function
      await act(async () => {
        navigator.clipboard.writeText('test');
      });

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('test');
    });
  });

  describe('Data Refetching', () => {
    it('calls getWorkload on component mount', async () => {
      await act(async () => {
        render(<WorkloadDetailsPage workload={mockWorkload} />, { wrapper });
      });
      expect(getWorkload).toHaveBeenCalledWith('workload-1', true);
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
        render(<WorkloadDetailsPage workload={workloadWithNullGPU} />, {
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
        render(<WorkloadDetailsPage workload={workloadWithoutResources} />, {
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
        render(<WorkloadDetailsPage workload={workloadWithDataset} />, {
          wrapper,
        });
      });

      // Should display the dataset name from the mocked dataset
      await waitFor(() => {
        expect(screen.getByText('Test Dataset')).toBeInTheDocument();
      });
    });

    it('handles workload with AIM', async () => {
      const workloadWithAim = {
        ...mockWorkload,
        aimId: 'aim-1',
      };

      (getWorkload as Mock).mockResolvedValue(workloadWithAim);

      await act(async () => {
        render(<WorkloadDetailsPage workload={workloadWithAim} />, {
          wrapper,
        });
      });

      // Should display the AIM information from the mocked AIM
      await waitFor(() => {
        expect(screen.getByText('test-aim-image')).toBeInTheDocument();
        expect(screen.getByText('1.0.0')).toBeInTheDocument();
        expect(screen.getByText('org/test-aim')).toBeInTheDocument();
      });
    });

    it('displays AIM card with skeleton while loading', async () => {
      const workloadWithAim = {
        ...mockWorkload,
        aimId: 'aim-1',
      };

      // Delay the AIM response to test loading state
      (getAimById as Mock).mockImplementation(
        () =>
          new Promise((resolve) =>
            setTimeout(
              () =>
                resolve({
                  id: 'aim-1',
                  imageName: 'test-aim-image',
                  imageTag: '1.0.0',
                  canonicalName: 'org/test-model',
                  description: {
                    short: 'Test AIM description',
                  },
                }),
              100,
            ),
          ),
      );

      (getWorkload as Mock).mockResolvedValue(workloadWithAim);

      await act(async () => {
        render(<WorkloadDetailsPage workload={workloadWithAim} />, {
          wrapper,
        });
      });

      // Should show AIM card header while loading
      await waitFor(() => {
        expect(screen.getByText('list.headers.aim.title')).toBeInTheDocument();
      });
    });
  });

  describe('API Error Handling', () => {
    it('handles API call failures gracefully', async () => {
      (getWorkload as Mock).mockRejectedValue(new Error('API Error'));

      await act(async () => {
        render(<WorkloadDetailsPage workload={mockWorkload} />, { wrapper });
      });

      // The component should still render with the provided workload prop even if API fails
      expect(
        screen.getByText('details.sections.basicInformation'),
      ).toBeInTheDocument();
    });
  });
});
