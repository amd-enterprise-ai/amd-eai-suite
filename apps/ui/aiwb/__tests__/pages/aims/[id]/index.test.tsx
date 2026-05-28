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
import { AIMServiceStatus } from '@/types/aims';
import type {
  AIMService,
  AIMClusterModel,
  AIMClusterServiceTemplate,
  ParsedAIM,
} from '@/types/aims';
import {
  getAimService,
  getAimClusterModel,
  getAimClusterServiceTemplates,
  getAimServiceHistory,
  aimParser,
  getAIMServiceStatusVariants,
} from '@/lib/app/aims';
import { useScalingConvergence } from '@/hooks/useScalingConvergence';
import AimDetailsPage from '@/pages/[project]/aims/[id]/index';
import wrapper from '@/__tests__/ProviderWrapper';
import '@testing-library/jest-dom';
import { Mock, vi } from 'vitest';

vi.mock('next/router', () => ({
  useRouter: vi.fn(),
}));

vi.mock('@/contexts/ProjectContext', async (importOriginal) => ({
  ...(await importOriginal()),
  useProject: vi.fn(),
}));

vi.mock('@/lib/app/aims', async (importOriginal) => ({
  ...(await importOriginal()),
  getAimService: vi.fn(),
  getAimClusterModel: vi.fn(),
  getAimClusterServiceTemplates: vi.fn(),
  getAimServiceHistory: vi.fn(),
  aimParser: vi.fn(),
  historicalAimParser: vi.fn(),
  undeployAim: vi.fn(),
  getAIMServiceStatusVariants: vi.fn(() => ({})),
}));

vi.mock('@/hooks/useScalingConvergence', () => ({
  useScalingConvergence: vi.fn(),
  CONVERGENCE_POLL_INTERVAL_MS: 5000,
}));

vi.mock('@/components/features/workloads/ScalingStatusCard', () => ({
  ScalingStatusCard: vi.fn(({ onSettingsSaved }) => (
    <div data-testid="scaling-status-card">
      <button
        data-testid="trigger-settings-saved"
        onClick={() =>
          onSettingsSaved?.({
            minReplicas: 2,
            maxReplicas: 5,
            metricQuery: 'vllm:num_requests_running',
            operationOverTime: 'avg',
            targetType: 'Value',
            targetValue: 10,
          })
        }
      >
        Save Settings
      </button>
    </div>
  )),
}));

vi.mock('@/components/features/workloads/DeleteWorkloadModal', () => ({
  __esModule: true,
  default: vi.fn(() => <div data-testid="delete-modal" />),
}));

vi.mock('@/components/features/workloads/WorkloadLogsModal', () => ({
  __esModule: true,
  default: vi.fn(() => <div data-testid="logs-modal" />),
}));

vi.mock('@/components/features/workloads/InferenceMetrics', () => ({
  __esModule: true,
  default: vi.fn(() => <div data-testid="inference-metrics" />),
}));

vi.mock('@amdenterpriseai/hooks', async (importOriginal) => ({
  ...(await importOriginal()),
  __esModule: true,
  useSystemToast: () => ({
    toast: mockToast,
  }),
}));

vi.mock('next-i18next', () => ({
  Trans: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useTranslation: () => ({
    t: (key: string, options?: any) => {
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

Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn().mockResolvedValue(undefined),
  },
});

const mockToast = {
  success: vi.fn(),
  error: vi.fn(),
  warning: vi.fn(),
};

const mockStartPolling = vi.fn();

const mockAimService: AIMService = {
  id: 'aim-service-1',
  metadata: {
    name: 'aim-llama-8b',
    namespace: 'test-project',
    uid: 'uid-1',
    labels: {},
    annotations: { 'eai.amd.com/submitter': 'test-user' },
    creationTimestamp: '2025-01-01T00:00:00Z',
    ownerReferences: [],
  },
  spec: {
    model: { name: 'aim-llama-8b' },
    replicas: 1,
    overrides: {},
    cacheModel: false,
    routing: { annotations: {}, enabled: false },
    runtimeConfigName: 'default',
    template: {},
    minReplicas: 1,
    maxReplicas: 5,
    autoScaling: {
      metrics: [
        {
          type: 'PodMetric',
          podmetric: {
            metric: {
              backend: 'opentelemetry',
              metricNames: ['vllm:num_requests_running'],
              query: 'vllm:num_requests_running',
              operationOverTime: 'avg',
            },
            target: { type: 'Value', value: '10' },
          },
        },
      ],
    },
  },
  status: {
    status: AIMServiceStatus.RUNNING,
    conditions: [
      {
        type: 'CacheReady',
        status: 'True',
        reason: 'CacheReady',
        message: 'Cache is ready',
        observedGeneration: 1,
        lastTransitionTime: '2025-01-01T00:00:00Z',
      },
      {
        type: 'InferenceReady',
        status: 'False',
        reason: 'InferenceFailed',
        message: 'Inference failed',
        observedGeneration: 1,
        lastTransitionTime: '2025-01-01T00:00:00Z',
      },
    ],
    runtime: {
      currentReplicas: 2,
      desiredReplicas: 3,
      minReplicas: 1,
      maxReplicas: 5,
    },
    resolvedModel: { name: 'aim-llama-8b' },
    resolvedTemplate: { name: 'template-1' },
  },
  clusterAuthGroupId: 'auth-group-1',
  endpoints: {
    external: 'https://example.com/aim',
    internal: 'http://aim.default.svc.cluster.local',
  },
};

const mockAimClusterModel: AIMClusterModel = {
  metadata: {
    name: 'aim-llama-8b',
    namespace: null,
    uid: 'uid-2',
    labels: {},
    annotations: {
      'aim.eai.amd.com/source-registry': 'ghcr.io',
      'aim.eai.amd.com/source-repository': 'amdenterpriseai/aim-llama-8b',
      'aim.eai.amd.com/source-tag': '0.7.0',
    },
    creationTimestamp: '2025-01-01T00:00:00Z',
    ownerReferences: [],
  },
  spec: {
    image: 'ghcr.io/amdenterpriseai/aim-llama-8b:0.7.0',
  },
  status: {
    status: 'Available' as any,
    imageMetadata: {
      model: {
        canonicalName: 'meta-llama/Llama-3.1-8B-Instruct',
        title: 'Llama 3.1 8B Instruct',
        tags: [],
        descriptionFull: 'Full description',
        hfTokenRequired: false,
      },
      oci: {
        title: 'Llama 3.1 8B Instruct',
        description: 'A large language model',
        version: '0.7.0',
      },
    } as any,
  },
};

const mockParsedAim: ParsedAIM = {
  model: 'aim-llama-8b',
  imageReference: 'ghcr.io/amdenterpriseai/aim-llama-8b:0.7.0',
  annotations: mockAimClusterModel.metadata.annotations,
  description: { short: 'A large language model', full: 'Full description' },
  title: 'Llama 3.1 8B Instruct',
  imageVersion: '0.7.0',
  canonicalName: 'meta-llama/Llama-3.1-8B-Instruct',
  tags: [],
  status: 'Available' as any,
  workloadStatuses: ['Deployed' as any],
  isPreview: false,
  isHfTokenRequired: false,
  deployedService: mockAimService,
  deployedServices: [mockAimService],
};

describe('AimDetailsPage', () => {
  const mockPush = vi.fn();
  const mockBack = vi.fn();
  const mockReload = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useRouter as Mock).mockReturnValue({
      query: { id: 'aim-service-1', project: 'test-project' },
      push: mockPush,
      back: mockBack,
      reload: mockReload,
    });
    (useProject as Mock).mockReturnValue({
      activeProject: 'test-project',
      projectPath: (path: string) =>
        `/test-project${path.startsWith('/') ? path : `/${path}`}`,
      projectUrl: (path: string) =>
        `/test-project${path.startsWith('/') ? path : `/${path}`}`,
    });
    (getAimService as Mock).mockResolvedValue(mockAimService);
    (getAimClusterModel as Mock).mockResolvedValue(mockAimClusterModel);
    (getAimClusterServiceTemplates as Mock).mockResolvedValue([]);
    (getAimServiceHistory as Mock).mockResolvedValue([]);
    (aimParser as Mock).mockReturnValue(mockParsedAim);
    (getAIMServiceStatusVariants as Mock).mockReturnValue({});
    (useScalingConvergence as Mock).mockReturnValue({
      startPolling: mockStartPolling,
    });
  });

  describe('Rendering', () => {
    it('renders AIM details with basic information', async () => {
      await act(async () => {
        render(<AimDetailsPage id="aim-service-1" />, { wrapper });
      });

      await waitFor(() => {
        expect(
          screen.getAllByText('meta-llama/Llama-3.1-8B-Instruct').length,
        ).toBeGreaterThan(0);
        expect(
          screen.getByText('details.sections.basicInformation'),
        ).toBeInTheDocument();
        expect(screen.getByText('details.sections.status')).toBeInTheDocument();
      });
    });

    it('renders profile section with model details', async () => {
      await act(async () => {
        render(<AimDetailsPage id="aim-service-1" />, { wrapper });
      });

      await waitFor(() => {
        expect(screen.getByText('details.profile.title')).toBeInTheDocument();
        expect(
          screen.getByText('details.profile.performanceMetric'),
        ).toBeInTheDocument();
        expect(
          screen.getByText('details.profile.accelerator'),
        ).toBeInTheDocument();
      });
    });

    it('renders output section with endpoints', async () => {
      await act(async () => {
        render(<AimDetailsPage id="aim-service-1" />, { wrapper });
      });

      await waitFor(() => {
        expect(screen.getByText('details.sections.output')).toBeInTheDocument();
        expect(
          screen.getByText('details.fields.externalHost'),
        ).toBeInTheDocument();
        expect(
          screen.getByText('details.fields.internalHost'),
        ).toBeInTheDocument();
      });
    });

    it('renders status section with conditions accordion', async () => {
      await act(async () => {
        render(<AimDetailsPage id="aim-service-1" />, { wrapper });
      });

      await waitFor(() => {
        expect(screen.getByText('details.sections.status')).toBeInTheDocument();
        expect(
          screen.getByText('list.headers.createdBy.title'),
        ).toBeInTheDocument();
      });
    });

    it('renders ScalingStatusCard when autoscaling is configured', async () => {
      await act(async () => {
        render(<AimDetailsPage id="aim-service-1" />, { wrapper });
      });

      await waitFor(() => {
        expect(screen.getByTestId('scaling-status-card')).toBeInTheDocument();
      });
    });

    it('renders action buttons', async () => {
      await act(async () => {
        render(<AimDetailsPage id="aim-service-1" />, { wrapper });
      });

      await waitFor(() => {
        expect(screen.getByText('list.actions.chat.label')).toBeInTheDocument();
        expect(screen.getByText('list.actions.logs.label')).toBeInTheDocument();
        expect(
          screen.getByText('list.actions.delete.label'),
        ).toBeInTheDocument();
      });
    });

    it('renders inference metrics for running service', async () => {
      await act(async () => {
        render(<AimDetailsPage id="aim-service-1" />, { wrapper });
      });

      await waitFor(() => {
        expect(screen.getByTestId('inference-metrics')).toBeInTheDocument();
      });
    });
  });

  describe('Error State', () => {
    it('renders error message when AIM cluster model fails to load', async () => {
      (getAimClusterModel as Mock).mockRejectedValue(new Error('Not Found'));

      await act(async () => {
        render(<AimDetailsPage id="aim-service-1" />, { wrapper });
      });

      await waitFor(() => {
        expect(
          screen.getByText('errors.workloadNotFound.title'),
        ).toBeInTheDocument();
      });
    });
  });

  describe('User Interactions', () => {
    it('navigates back when back button is clicked', async () => {
      await act(async () => {
        render(<AimDetailsPage id="aim-service-1" />, { wrapper });
      });

      const backButton = await screen.findByRole('button', {
        name: (_content, element) =>
          element?.querySelector('.tabler-icon-arrow-left') !== null,
      });
      await act(async () => {
        fireEvent.click(backButton);
      });

      expect(mockBack).toHaveBeenCalled();
    });

    it('opens logs modal when logs button is clicked', async () => {
      await act(async () => {
        render(<AimDetailsPage id="aim-service-1" />, { wrapper });
      });

      const logsButton = await waitFor(() =>
        screen.getByText('list.actions.logs.label'),
      );

      await act(async () => {
        fireEvent.click(logsButton);
      });

      await waitFor(() => {
        expect(screen.getByTestId('logs-modal')).toBeInTheDocument();
      });
    });
  });

  describe('Convergence Polling', () => {
    it('calls startPolling and refetch when settings are saved', async () => {
      await act(async () => {
        render(<AimDetailsPage id="aim-service-1" />, { wrapper });
      });

      const saveButton = await waitFor(() =>
        screen.getByTestId('trigger-settings-saved'),
      );

      await act(async () => {
        fireEvent.click(saveButton);
      });

      expect(mockStartPolling).toHaveBeenCalledWith({
        minReplicas: 2,
        maxReplicas: 5,
        metricQuery: 'vllm:num_requests_running',
        operationOverTime: 'avg',
        targetType: 'Value',
        targetValue: 10,
      });
    });

    it('passes stopConvergencePolling as onConverged to useScalingConvergence', async () => {
      await act(async () => {
        render(<AimDetailsPage id="aim-service-1" />, { wrapper });
      });

      expect(useScalingConvergence as Mock).toHaveBeenCalledWith(
        expect.objectContaining({
          onConverged: expect.any(Function),
          onTimeout: expect.any(Function),
          isPolling: false,
        }),
      );
    });

    it('passes handleConvergenceTimeout as onTimeout to useScalingConvergence', async () => {
      let capturedOnTimeout: (() => void) | undefined;
      (useScalingConvergence as Mock).mockImplementation((params) => {
        capturedOnTimeout = params.onTimeout;
        return { startPolling: mockStartPolling };
      });

      await act(async () => {
        render(<AimDetailsPage id="aim-service-1" />, { wrapper });
      });

      expect(capturedOnTimeout).toBeDefined();
      act(() => {
        capturedOnTimeout!();
      });

      expect(mockToast.warning).toHaveBeenCalledWith(
        'autoscaling:notifications.convergenceTimeout',
      );
    });
  });

  describe('Service without autoscaling', () => {
    it('does not render ScalingStatusCard when autoscaling is absent', async () => {
      const serviceWithoutAutoscaling = {
        ...mockAimService,
        spec: { ...mockAimService.spec, autoScaling: undefined },
      };
      (getAimService as Mock).mockResolvedValue(serviceWithoutAutoscaling);

      await act(async () => {
        render(<AimDetailsPage id="aim-service-1" />, { wrapper });
      });

      await waitFor(() => {
        expect(
          screen.queryByTestId('scaling-status-card'),
        ).not.toBeInTheDocument();
      });
    });
  });

  describe('Service without endpoints', () => {
    it('does not render output section when endpoints are missing', async () => {
      const serviceWithoutEndpoints = {
        ...mockAimService,
        endpoints: { internal: '', external: '' },
      };
      (getAimService as Mock).mockResolvedValue(serviceWithoutEndpoints);
      (aimParser as Mock).mockReturnValue({
        ...mockParsedAim,
        deployedService: serviceWithoutEndpoints,
        deployedServices: [serviceWithoutEndpoints],
      });

      await act(async () => {
        render(<AimDetailsPage id="aim-service-1" />, { wrapper });
      });

      await waitFor(() => {
        expect(
          screen.queryByText('details.sections.output'),
        ).not.toBeInTheDocument();
      });
    });
  });
});
