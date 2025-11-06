// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';
import { DeployAIMDrawer } from '@/components/features/models/DeployAIMDrawer';
import { mockAims } from '@/__mocks__/services/app/aims.data';
import wrapper from '@/__tests__/ProviderWrapper';

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
  fetchProjectSecrets: vi.fn().mockResolvedValue({ projectSecrets: [] }),
  createSecret: vi.fn(),
}));

vi.mock('@/services/app/aims', () => ({
  deployAim: vi.fn(),
}));

describe('DeployAIMDrawer', () => {
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
});
