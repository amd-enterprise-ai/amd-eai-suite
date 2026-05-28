// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { SecretUseCase } from '@amdenterpriseai/types';
import { DeployAIMDrawer } from '@/components/features/models/DeployAIMDrawer';
import {
  mockAims,
  mockAggregatedAims,
  mockMixedSupportAggregatedAim,
} from '@/__mocks__/services/app/aims.data';
import wrapper from '@/__tests__/ProviderWrapper';
import { fetchProjectSecrets, createProjectSecret } from '@/lib/app/secrets';
import { Mock } from 'vitest';
import {
  AIMClusterServiceTemplate,
  AIMMetric,
  AIMService,
  AIMStatus,
} from '@/types/aims';
import * as aimsLib from '@/lib/app/aims';

vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock('@/components/shared/ModelIcons', () => ({
  ModelIcon: ({ iconName, width, height }: any) => (
    <div
      data-testid={`model-icon-${iconName || 'default'}`}
      style={{ width: `${width}px`, height: `${height}px` }}
    >
      {iconName || 'default'} icon
    </div>
  ),
}));

const mockToast = {
  success: vi.fn(),
  error: vi.fn(),
};

vi.mock('@amdenterpriseai/hooks', async (importOriginal) => ({
  ...(await importOriginal()),
  useSystemToast: () => ({
    toast: mockToast,
  }),
}));

vi.mock('@/contexts/ProjectContext', () => ({
  useProject: () => ({
    activeProject: 'test-project',
    projects: [{ id: 'test-project', name: 'Test Project' }],
  }),
}));

vi.mock('@/lib/app/secrets', () => ({
  fetchProjectSecrets: vi.fn(),
  createProjectSecret: vi.fn(),
}));

// Mock service templates
const mockServiceTemplates: AIMClusterServiceTemplate[] = [
  {
    metadata: { name: 'template-latency', labels: {} },
    spec: { modelName: 'test-model', metric: AIMMetric.Latency },
    status: { status: 'Ready' },
  },
  {
    metadata: { name: 'template-throughput', labels: {} },
    spec: { modelName: 'test-model', metric: AIMMetric.Throughput },
    status: { status: 'Ready' },
  },
];

describe('DeployAIMDrawer', () => {
  let getAimClusterServiceTemplatesSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockToast.success.mockClear();
    mockToast.error.mockClear();
    (fetchProjectSecrets as Mock).mockResolvedValue({ data: [] });
    (createProjectSecret as Mock).mockResolvedValue({
      id: 'new-secret-id',
      name: 'test-hf-token',
    });
    // Default: no service templates (no metrics available)
    getAimClusterServiceTemplatesSpy = vi
      .spyOn(aimsLib, 'getAimClusterServiceTemplates')
      .mockResolvedValue([]);
  });

  it('renders drawer when open', () => {
    const aggregatedAim = mockAggregatedAims[0];
    render(<DeployAIMDrawer isOpen={true} aggregatedAim={aggregatedAim} />, {
      wrapper,
    });

    expect(screen.getByText('deployAIMDrawer.title')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    const aggregatedAim = mockAggregatedAims[0];
    render(<DeployAIMDrawer isOpen={false} aggregatedAim={aggregatedAim} />, {
      wrapper,
    });

    expect(screen.queryByText('deployAIMDrawer.title')).not.toBeInTheDocument();
  });

  it('renders HuggingFace token field when isHfTokenRequired is true', async () => {
    const aimWithTokenRequired = {
      ...mockAims[0],
      isHfTokenRequired: true,
      isLatest: true,
    };
    const aggregatedAim = {
      ...mockAggregatedAims[0],
      parsedAIMs: [aimWithTokenRequired],
      latestAim: aimWithTokenRequired,
    };
    render(<DeployAIMDrawer isOpen={true} aggregatedAim={aggregatedAim} />, {
      wrapper,
    });

    await waitFor(() => {
      expect(
        screen.getByText('deployAIMDrawer.fields.huggingFaceToken.title'),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByLabelText(/huggingFaceTokenDrawer.fields.name.label/i),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText(/huggingFaceTokenDrawer.fields.token.label/i),
    ).toBeInTheDocument();
  });

  it('does not render HuggingFace token field when isHfTokenRequired is false', async () => {
    const aimWithoutTokenRequired = {
      ...mockAims[0],
      isHfTokenRequired: false,
      isLatest: true,
    };
    const aggregatedAim = {
      ...mockAggregatedAims[0],
      parsedAIMs: [aimWithoutTokenRequired],
      latestAim: aimWithoutTokenRequired,
    };
    render(<DeployAIMDrawer isOpen={true} aggregatedAim={aggregatedAim} />, {
      wrapper,
    });

    await waitFor(() => {
      expect(screen.getByText('deployAIMDrawer.title')).toBeInTheDocument();
    });

    expect(
      screen.queryByText('deployAIMDrawer.fields.huggingFaceToken.title'),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText(/huggingFaceTokenDrawer.fields.name.label/i),
    ).not.toBeInTheDocument();
  });

  it('displays aim information correctly', () => {
    const aggregatedAim = mockAggregatedAims[0];
    const displayAim =
      aggregatedAim.latestAim ??
      aggregatedAim.parsedAIMs.find((a) => a.status === AIMStatus.READY) ??
      aggregatedAim.parsedAIMs[0]!;
    render(<DeployAIMDrawer isOpen={true} aggregatedAim={aggregatedAim} />, {
      wrapper,
    });

    expect(screen.getByText(displayAim.title)).toBeInTheDocument();
    expect(screen.getByText(displayAim.description.short)).toBeInTheDocument();
    expect(screen.getByText(displayAim.description.full)).toBeInTheDocument();
  });

  it('renders metric dropdown when service templates are available', async () => {
    getAimClusterServiceTemplatesSpy.mockResolvedValueOnce(
      mockServiceTemplates,
    );

    const aggregatedAim = mockAggregatedAims[0];
    render(<DeployAIMDrawer isOpen={true} aggregatedAim={aggregatedAim} />, {
      wrapper,
    });

    await waitFor(() => {
      expect(
        screen.getByText('deployAIMDrawer.fields.metric.title'),
      ).toBeInTheDocument();
    });
  });

  it('does not render metric dropdown when no service templates are available', async () => {
    const aggregatedAim = mockAggregatedAims[0];
    render(<DeployAIMDrawer isOpen={true} aggregatedAim={aggregatedAim} />, {
      wrapper,
    });

    // Wait for the query to complete
    await waitFor(() => {
      expect(getAimClusterServiceTemplatesSpy).toHaveBeenCalled();
    });

    expect(
      screen.queryByText('deployAIMDrawer.fields.metric.title'),
    ).not.toBeInTheDocument();
  });

  it('disables deploy button when no service templates are available', async () => {
    const aggregatedAim = mockAggregatedAims[0];
    render(<DeployAIMDrawer isOpen={true} aggregatedAim={aggregatedAim} />, {
      wrapper,
    });

    // Wait for the "no templates" error toast to ensure loading has finished
    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith(
        'deployAIMDrawer.notifications.noTemplatesDescription',
      );
    });

    // Deploy button should be disabled after templates loading has settled
    const deployButton = screen.getByText('deployAIMDrawer.actions.deploy');
    expect(deployButton).toBeDisabled();
  });

  it('shows error toast when no service templates are available', async () => {
    const aggregatedAim = mockAggregatedAims[0];
    render(<DeployAIMDrawer isOpen={true} aggregatedAim={aggregatedAim} />, {
      wrapper,
    });

    // Error toast should be called
    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith(
        'deployAIMDrawer.notifications.noTemplatesDescription',
      );
    });
  });

  it('does not render metric dropdown when all templates are NotAvailable', async () => {
    getAimClusterServiceTemplatesSpy.mockResolvedValueOnce([
      {
        metadata: { name: 'template-latency', labels: {} },
        spec: { modelName: 'test-model', metric: AIMMetric.Latency },
        status: { status: 'NotAvailable' },
      },
      {
        metadata: { name: 'template-throughput', labels: {} },
        spec: { modelName: 'test-model', metric: AIMMetric.Throughput },
        status: { status: 'NotAvailable' },
      },
    ]);

    const aggregatedAim = mockAggregatedAims[0];
    render(<DeployAIMDrawer isOpen={true} aggregatedAim={aggregatedAim} />, {
      wrapper,
    });

    await waitFor(() => {
      expect(getAimClusterServiceTemplatesSpy).toHaveBeenCalled();
    });

    expect(
      screen.queryByText('deployAIMDrawer.fields.metric.title'),
    ).not.toBeInTheDocument();
  });

  it('disables deploy button and shows error toast when all templates are NotAvailable', async () => {
    getAimClusterServiceTemplatesSpy.mockResolvedValueOnce([
      {
        metadata: { name: 'template-latency', labels: {} },
        spec: { modelName: 'test-model', metric: AIMMetric.Latency },
        status: { status: 'NotAvailable' },
      },
      {
        metadata: { name: 'template-throughput', labels: {} },
        spec: { modelName: 'test-model', metric: AIMMetric.Throughput },
        status: { status: 'NotAvailable' },
      },
    ]);

    const aggregatedAim = mockAggregatedAims[0];
    render(<DeployAIMDrawer isOpen={true} aggregatedAim={aggregatedAim} />, {
      wrapper,
    });

    // Error toast should be called
    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith(
        'deployAIMDrawer.notifications.noTemplatesDescription',
      );
    });

    // Deploy button should be disabled after templates loading has settled
    const deployButton = screen.getByText('deployAIMDrawer.actions.deploy');
    expect(deployButton).toBeDisabled();
  });

  it('enables deploy button when ready templates are available', async () => {
    getAimClusterServiceTemplatesSpy.mockResolvedValueOnce([
      {
        metadata: { name: 'template-latency', labels: {} },
        spec: { modelName: 'test-model', metric: AIMMetric.Latency },
        status: { status: 'Ready' },
      },
    ]);

    const aggregatedAim = mockAggregatedAims[0];
    render(<DeployAIMDrawer isOpen={true} aggregatedAim={aggregatedAim} />, {
      wrapper,
    });

    // Wait for deploy button to be enabled
    const deployButton = await screen.findByText(
      'deployAIMDrawer.actions.deploy',
    );
    await waitFor(() => {
      expect(deployButton).not.toBeDisabled();
    });

    // Error toast should NOT be called
    expect(mockToast.error).not.toHaveBeenCalled();
  });

  it('passes a single selected image pull secret to deployAim', async () => {
    const deployAimSpy = vi
      .spyOn(aimsLib, 'deployAim')
      .mockResolvedValue(undefined as unknown as AIMService);

    const base = mockAggregatedAims[0];
    const parsedNoHf = base.parsedAIMs.map((a) => ({
      ...a,
      isHfTokenRequired: false,
    }));
    const aggregatedAim = {
      ...base,
      parsedAIMs: parsedNoHf,
      latestAim: parsedNoHf[0],
      aggregated: { ...base.aggregated, isHfTokenRequired: false },
    };

    const pullSecretName = 'registry-pull-one';
    (fetchProjectSecrets as Mock).mockResolvedValue({
      data: [
        {
          metadata: {
            name: pullSecretName,
            namespace: 'test-project',
            creationTimestamp: '2023-01-01T00:00:00Z',
          },
          useCase: SecretUseCase.IMAGE_PULL_SECRET,
        },
      ],
    });

    getAimClusterServiceTemplatesSpy.mockResolvedValueOnce([
      {
        metadata: { name: 'template-latency', labels: {} },
        spec: { modelName: 'test-model', metric: AIMMetric.Latency },
        status: { status: 'Ready' },
      },
    ]);

    render(<DeployAIMDrawer isOpen={true} aggregatedAim={aggregatedAim} />, {
      wrapper,
    });

    const deployButton = await screen.findByRole('button', {
      name: 'deployAIMDrawer.actions.deploy',
    });
    await waitFor(() => {
      expect(deployButton).not.toBeDisabled();
    });

    // Match FinetuneDrawer (data-testid + fireEvent); role-based queries time out for this Select in jsdom.
    fireEvent.click(screen.getByTestId('deployAimImagePullSecretsSelect'));
    fireEvent.click(
      await screen.findByTestId(
        `deployAimImagePullSecretOption-${pullSecretName}`,
      ),
    );

    fireEvent.click(deployButton);

    await waitFor(() => {
      expect(deployAimSpy).toHaveBeenCalled();
    });

    expect(deployAimSpy).toHaveBeenCalledWith(
      'test-project',
      expect.objectContaining({
        imagePullSecrets: [pullSecretName],
      }),
    );

    deployAimSpy.mockRestore();
  });

  it('only shows metrics from Ready templates, ignoring NotAvailable ones', async () => {
    getAimClusterServiceTemplatesSpy.mockResolvedValueOnce([
      {
        metadata: { name: 'template-latency', labels: {} },
        spec: { modelName: 'test-model', metric: AIMMetric.Latency },
        status: { status: 'Ready' },
      },
      {
        metadata: { name: 'template-throughput', labels: {} },
        spec: { modelName: 'test-model', metric: AIMMetric.Throughput },
        status: { status: 'NotAvailable' },
      },
    ]);

    const aggregatedAim = mockAggregatedAims[0];
    render(<DeployAIMDrawer isOpen={true} aggregatedAim={aggregatedAim} />, {
      wrapper,
    });

    await waitFor(() => {
      expect(
        screen.getByText('deployAIMDrawer.fields.metric.title'),
      ).toBeInTheDocument();
    });
  });

  it('renders metric dropdown with single metric option', async () => {
    // Mock single service template
    getAimClusterServiceTemplatesSpy.mockResolvedValueOnce([
      {
        metadata: { name: 'template-latency', labels: {} },
        spec: { modelName: 'test-model', metric: AIMMetric.Latency },
        status: { status: 'Ready' },
      },
    ]);

    const aggregatedAim = mockAggregatedAims[0];
    render(<DeployAIMDrawer isOpen={true} aggregatedAim={aggregatedAim} />, {
      wrapper,
    });

    await waitFor(() => {
      expect(
        screen.getByText('deployAIMDrawer.fields.metric.title'),
      ).toBeInTheDocument();
    });
  });

  describe('unoptimized profile logic', () => {
    it('shows warning Alert when all templates are unoptimized (no profile)', async () => {
      getAimClusterServiceTemplatesSpy.mockResolvedValueOnce([
        {
          metadata: { name: 'template-latency', labels: {} },
          spec: { modelName: 'test-model', metric: AIMMetric.Latency },
          status: { status: 'Ready' },
        },
      ]);

      const aggregatedAim = mockAggregatedAims[0];
      render(<DeployAIMDrawer isOpen={true} aggregatedAim={aggregatedAim} />, {
        wrapper,
      });

      await waitFor(() => {
        expect(
          screen.getByText('deployAIMDrawer.fields.metric.notOptimized'),
        ).toBeInTheDocument();
      });
      expect(
        screen.getAllByText('deployAIMDrawer.fields.metric.unoptimizedLabel')
          .length,
      ).toBeGreaterThanOrEqual(1);
    });

    it('shows warning Alert when all templates have profile type other than optimized', async () => {
      getAimClusterServiceTemplatesSpy.mockResolvedValueOnce([
        {
          metadata: { name: 'template-latency', labels: {} },
          spec: { modelName: 'test-model', metric: AIMMetric.Latency },
          status: {
            status: 'Ready',
            profile: { metadata: { type: 'preview' } },
          },
        },
      ]);

      const aggregatedAim = mockAggregatedAims[0];
      render(<DeployAIMDrawer isOpen={true} aggregatedAim={aggregatedAim} />, {
        wrapper,
      });

      await waitFor(() => {
        expect(
          screen.getByText('deployAIMDrawer.fields.metric.notOptimized'),
        ).toBeInTheDocument();
      });
    });

    it('does not show warning Alert when at least one template is optimized and no metric selected', async () => {
      getAimClusterServiceTemplatesSpy.mockResolvedValueOnce([
        {
          metadata: { name: 'template-latency', labels: {} },
          spec: { modelName: 'test-model', metric: AIMMetric.Latency },
          status: {
            status: 'Ready',
            profile: { metadata: { type: 'optimized' } },
          },
        },
        {
          metadata: { name: 'template-throughput', labels: {} },
          spec: { modelName: 'test-model', metric: AIMMetric.Throughput },
          status: {
            status: 'Ready',
            profile: { metadata: { type: 'preview' } },
          },
        },
      ]);

      const aggregatedAim = mockAggregatedAims[0];
      render(<DeployAIMDrawer isOpen={true} aggregatedAim={aggregatedAim} />, {
        wrapper,
      });

      await waitFor(() => {
        expect(
          screen.getByText('deployAIMDrawer.fields.metric.title'),
        ).toBeInTheDocument();
      });

      expect(
        screen.queryByText('deployAIMDrawer.fields.metric.notOptimized'),
      ).not.toBeInTheDocument();
    });

    it('shows Unoptimized profile tag in metric section when all profiles are unoptimized', async () => {
      getAimClusterServiceTemplatesSpy.mockResolvedValueOnce(
        mockServiceTemplates,
      );

      const aggregatedAim = mockAggregatedAims[0];
      render(<DeployAIMDrawer isOpen={true} aggregatedAim={aggregatedAim} />, {
        wrapper,
      });

      await waitFor(() => {
        expect(
          screen.getByText('deployAIMDrawer.fields.metric.title'),
        ).toBeInTheDocument();
      });

      expect(
        screen.getAllByText('deployAIMDrawer.fields.metric.unoptimizedLabel')
          .length,
      ).toBeGreaterThanOrEqual(1);
    });

    it('only Ready templates are used for metrics (NotAvailable are excluded)', async () => {
      getAimClusterServiceTemplatesSpy.mockResolvedValueOnce([
        {
          metadata: { name: 'latency-ready', labels: {} },
          spec: { modelName: 'test-model', metric: AIMMetric.Latency },
          status: {
            status: 'Ready',
            profile: { metadata: { type: 'optimized' } },
          },
        },
        {
          metadata: { name: 'throughput-not-available', labels: {} },
          spec: { modelName: 'test-model', metric: AIMMetric.Throughput },
          status: { status: 'NotAvailable' },
        },
      ]);

      const aggregatedAim = mockAggregatedAims[0];
      render(<DeployAIMDrawer isOpen={true} aggregatedAim={aggregatedAim} />, {
        wrapper,
      });

      await waitFor(() => {
        expect(
          screen.getByText('deployAIMDrawer.fields.metric.title'),
        ).toBeInTheDocument();
      });

      // Only latency is Ready and optimized; NotAvailable throughput is excluded, so no warning
      expect(
        screen.queryByText('deployAIMDrawer.fields.metric.notOptimized'),
      ).not.toBeInTheDocument();
    });

    it('templates with undefined spec.metric do not affect metric options', async () => {
      getAimClusterServiceTemplatesSpy.mockResolvedValueOnce([
        {
          metadata: { name: 'no-metric', labels: {} },
          spec: {
            modelName: 'test-model',
          } as AIMClusterServiceTemplate['spec'],
          status: {
            status: 'Ready',
            profile: { metadata: { type: 'optimized' } },
          },
        },
        {
          metadata: { name: 'latency-ok', labels: {} },
          spec: { modelName: 'test-model', metric: AIMMetric.Latency },
          status: {
            status: 'Ready',
            profile: { metadata: { type: 'optimized' } },
          },
        },
      ]);

      const aggregatedAim = mockAggregatedAims[0];
      render(<DeployAIMDrawer isOpen={true} aggregatedAim={aggregatedAim} />, {
        wrapper,
      });

      await waitFor(() => {
        expect(
          screen.getByText('deployAIMDrawer.fields.metric.title'),
        ).toBeInTheDocument();
      });

      // One Ready template has no metric (skipped), one has latency (optimized); no warning
      expect(
        screen.queryByText('deployAIMDrawer.fields.metric.notOptimized'),
      ).not.toBeInTheDocument();
    });
  });

  it('defaults to latest supported version for mixed-support models', () => {
    render(
      <DeployAIMDrawer
        isOpen={true}
        aggregatedAim={mockMixedSupportAggregatedAim}
      />,
      { wrapper },
    );

    const supportedVersion = mockMixedSupportAggregatedAim.parsedAIMs.find(
      (aim) => aim.isLatest,
    );
    expect(screen.getByText(supportedVersion!.title)).toBeInTheDocument();
  });

  it('renders the version dropdown with both supported and unsupported versions', () => {
    render(
      <DeployAIMDrawer
        isOpen={true}
        aggregatedAim={mockMixedSupportAggregatedAim}
      />,
      { wrapper },
    );

    const versionLabels = screen.getAllByText(
      'deployAIMDrawer.fields.version.title',
    );
    expect(versionLabels.length).toBeGreaterThan(0);
  });
});
