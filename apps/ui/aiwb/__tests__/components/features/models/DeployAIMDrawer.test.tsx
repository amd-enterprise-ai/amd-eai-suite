// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen, waitFor } from '@testing-library/react';
import { DeployAIMDrawer } from '@/components/features/models/DeployAIMDrawer';
import {
  mockAims,
  mockAggregatedAims,
  mockMixedSupportAggregatedAim,
} from '@/__mocks__/services/app/aims.data';
import wrapper from '@/__tests__/ProviderWrapper';
import { SecretType } from '@amdenterpriseai/types';
import { fetchProjectSecrets, createProjectSecret } from '@/lib/app/secrets';
import { Mock } from 'vitest';
import { AIMClusterServiceTemplate, AIMMetric, AIMStatus } from '@/types/aims';
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

vi.mock('@amdenterpriseai/components', async (importOriginal) => ({
  ...(await importOriginal()),
  HuggingFaceTokenSelector: () => (
    <div data-testid="huggingface-token-selector">
      <div>huggingFaceTokenDrawer.fields.existingToken.label</div>
    </div>
  ),
}));

vi.mock('@amdenterpriseai/hooks', async (importOriginal) => ({
  ...(await importOriginal()),
  useSystemToast: () => ({
    toast: {
      success: vi.fn(),
      error: vi.fn(),
    },
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
  beforeEach(() => {
    vi.clearAllMocks();
    (fetchProjectSecrets as Mock).mockResolvedValue({ projectSecrets: [] });
    (createProjectSecret as Mock).mockResolvedValue({
      id: 'new-secret-id',
      name: 'test-hf-token',
    });
    // Default: no service templates (no metrics available)
    vi.spyOn(aimsLib, 'getAimServiceTemplates').mockResolvedValue([]);
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

  it('renders HuggingFace token field when isHfTokenRequired is true', () => {
    const aimWithTokenRequired = {
      ...mockAims[0],
      isHfTokenRequired: true,
      isLatest: true,
    };
    const aggregatedAim = {
      ...mockAggregatedAims[0],
      parsedAIMs: [aimWithTokenRequired],
    };
    render(<DeployAIMDrawer isOpen={true} aggregatedAim={aggregatedAim} />, {
      wrapper,
    });

    // Check if HuggingFace token selector is present
    expect(
      screen.getByText('huggingFaceTokenDrawer.fields.existingToken.label'),
    ).toBeInTheDocument();
  });

  it('does not render HuggingFace token field when isHfTokenRequired is false', () => {
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

    // Check if HuggingFace token selector is not present
    expect(
      screen.queryByText('huggingFaceTokenDrawer.fields.existingToken.label'),
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
    // Mock service templates with metrics
    vi.spyOn(aimsLib, 'getAimServiceTemplates').mockResolvedValue(
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
    // Mock empty service templates
    vi.spyOn(aimsLib, 'getAimServiceTemplates').mockResolvedValue([]);

    const aggregatedAim = mockAggregatedAims[0];
    render(<DeployAIMDrawer isOpen={true} aggregatedAim={aggregatedAim} />, {
      wrapper,
    });

    // Wait for the query to complete
    await waitFor(() => {
      expect(aimsLib.getAimServiceTemplates).toHaveBeenCalled();
    });

    expect(
      screen.queryByText('deployAIMDrawer.fields.metric.title'),
    ).not.toBeInTheDocument();
  });

  it('does not render metric dropdown when all templates are NotAvailable', async () => {
    vi.spyOn(aimsLib, 'getAimServiceTemplates').mockResolvedValue([
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
      expect(aimsLib.getAimServiceTemplates).toHaveBeenCalled();
    });

    expect(
      screen.queryByText('deployAIMDrawer.fields.metric.title'),
    ).not.toBeInTheDocument();
  });

  it('only shows metrics from Ready templates, ignoring NotAvailable ones', async () => {
    vi.spyOn(aimsLib, 'getAimServiceTemplates').mockResolvedValue([
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
    vi.spyOn(aimsLib, 'getAimServiceTemplates').mockResolvedValue([
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
      vi.spyOn(aimsLib, 'getAimServiceTemplates').mockResolvedValue([
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
      vi.spyOn(aimsLib, 'getAimServiceTemplates').mockResolvedValue([
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
      vi.spyOn(aimsLib, 'getAimServiceTemplates').mockResolvedValue([
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
      vi.spyOn(aimsLib, 'getAimServiceTemplates').mockResolvedValue(
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
      vi.spyOn(aimsLib, 'getAimServiceTemplates').mockResolvedValue([
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
      vi.spyOn(aimsLib, 'getAimServiceTemplates').mockResolvedValue([
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
