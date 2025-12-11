// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { DeployAIMDrawer } from '@/components/features/models/DeployAIMDrawer';
import { mockAims } from '@/__mocks__/services/app/aims.data';
import wrapper from '@/__tests__/ProviderWrapper';
import { SecretType } from '@/types/enums/secrets';
import {
  fetchProjectSecrets,
  createProjectSecret,
} from '@/services/app/secrets';
import { Mock } from 'vitest';

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

vi.mock('@/components/shared/HuggingFaceTokenSelector', () => ({
  HuggingFaceTokenSelector: () => (
    <div data-testid="huggingface-token-selector">
      <div>huggingFaceTokenDrawer.fields.existingToken.label</div>
    </div>
  ),
}));

vi.mock('@/hooks/useSystemToast', () => ({
  default: () => ({
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

vi.mock('@/services/app/secrets', () => ({
  fetchProjectSecrets: vi.fn(),
  createProjectSecret: vi.fn(),
}));

vi.mock('@/services/app/aims', () => ({
  deployAim: vi.fn(),
}));

describe('DeployAIMDrawer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (fetchProjectSecrets as Mock).mockResolvedValue({ projectSecrets: [] });
    (createProjectSecret as Mock).mockResolvedValue({
      id: 'new-secret-id',
      name: 'test-hf-token',
    });
  });

  it('renders drawer when open', () => {
    const aim = mockAims[0];
    render(<DeployAIMDrawer isOpen={true} aim={aim} />, { wrapper });

    expect(screen.getByText('deployAIMDrawer.title')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    const aim = mockAims[0];
    render(<DeployAIMDrawer isOpen={false} aim={aim} />, { wrapper });

    expect(screen.queryByText('deployAIMDrawer.title')).not.toBeInTheDocument();
  });

  it('renders HuggingFace token field when isHfTokenRequired is true', () => {
    const aimWithTokenRequired = {
      ...mockAims[0],
      isHfTokenRequired: true,
    };
    render(<DeployAIMDrawer isOpen={true} aim={aimWithTokenRequired} />, {
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
    };
    render(<DeployAIMDrawer isOpen={true} aim={aimWithoutTokenRequired} />, {
      wrapper,
    });

    // Check if HuggingFace token selector is not present
    expect(
      screen.queryByText('huggingFaceTokenDrawer.fields.existingToken.label'),
    ).not.toBeInTheDocument();
  });

  it('displays aim information correctly', () => {
    const aim = mockAims[0];
    render(<DeployAIMDrawer isOpen={true} aim={aim} />, { wrapper });

    expect(screen.getByText(aim.title)).toBeInTheDocument();
    expect(screen.getByText(aim.description.short)).toBeInTheDocument();
    expect(screen.getByText(aim.description.full)).toBeInTheDocument();
  });

  it('renders metric dropdown when availableMetrics has options', () => {
    const aimWithMetrics = {
      ...mockAims[0],
      availableMetrics: ['latency', 'throughput'],
      recommendedDeployments: [
        {
          gpuModel: 'MI300X',
          gpuCount: 1,
          precision: 'fp8',
          metric: 'latency',
          description: 'Optimized for latency',
        },
        {
          gpuModel: 'MI300X',
          gpuCount: 1,
          precision: 'fp8',
          metric: 'throughput',
          description: 'Optimized for throughput',
        },
      ],
    };
    render(<DeployAIMDrawer isOpen={true} aim={aimWithMetrics} />, {
      wrapper,
    });

    expect(
      screen.getByText('deployAIMDrawer.fields.metric.title'),
    ).toBeInTheDocument();
  });

  it('does not render metric dropdown when availableMetrics is empty', () => {
    const aimWithoutMetrics = {
      ...mockAims[0],
      availableMetrics: [],
      recommendedDeployments: [],
    };
    render(<DeployAIMDrawer isOpen={true} aim={aimWithoutMetrics} />, {
      wrapper,
    });

    expect(
      screen.queryByText('deployAIMDrawer.fields.metric.title'),
    ).not.toBeInTheDocument();
  });

  it('renders experimental deployment toggle', () => {
    const aim = mockAims[0];
    render(<DeployAIMDrawer isOpen={true} aim={aim} />, { wrapper });

    expect(
      screen.getByText('deployAIMDrawer.fields.experimentalDeployment.title'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('deployAIMDrawer.fields.experimentalDeployment.label'),
    ).toBeInTheDocument();
  });

  it('experimental deployment toggle defaults to false', () => {
    const aim = mockAims[0];
    render(<DeployAIMDrawer isOpen={true} aim={aim} />, { wrapper });

    const toggle = screen.getByRole('switch', {
      name: 'deployAIMDrawer.fields.experimentalDeployment.label',
    });
    expect(toggle).not.toBeChecked();
  });

  it('can toggle experimental deployment on and off', async () => {
    const aim = mockAims[0];
    render(<DeployAIMDrawer isOpen={true} aim={aim} />, { wrapper });

    const toggle = screen.getByRole('switch', {
      name: 'deployAIMDrawer.fields.experimentalDeployment.label',
    });

    // Initially unchecked
    expect(toggle).not.toBeChecked();

    // Toggle on
    fireEvent.click(toggle);
    await waitFor(() => {
      expect(toggle).toBeChecked();
    });

    // Toggle off
    fireEvent.click(toggle);
    await waitFor(() => {
      expect(toggle).not.toBeChecked();
    });
  });

  it('renders metric dropdown with single metric option', () => {
    const aimWithSingleMetric = {
      ...mockAims[0],
      availableMetrics: ['latency'],
      recommendedDeployments: [
        {
          gpuModel: 'MI300X',
          gpuCount: 1,
          precision: 'fp8',
          metric: 'latency',
          description: 'Optimized for latency',
        },
      ],
    };
    render(<DeployAIMDrawer isOpen={true} aim={aimWithSingleMetric} />, {
      wrapper,
    });

    expect(
      screen.getByText('deployAIMDrawer.fields.metric.title'),
    ).toBeInTheDocument();
  });
});
