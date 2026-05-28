// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen, waitFor } from '@testing-library/react';

import ModelsPage from '@/pages/[project]/models';
import { describe, expect, it, vi } from 'vitest';
import wrapper from '@/__tests__/ProviderWrapper';

// Mock CustomModels - now takes no props
vi.mock('@/components/features/models/CustomModels', () => ({
  default: () => (
    <div data-testid="custom-models">
      <h2>Custom Models</h2>
    </div>
  ),
}));

// Mock AIMCatalog
vi.mock('@/components/features/models/AIMCatalog', () => ({
  default: () => (
    <div data-testid="aim-catalog">
      <h2>AIM Catalog</h2>
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

const mockPush = vi.fn();
const mockRouter = {
  query: { tab: 'aim-catalog' },
  push: mockPush,
  pathname: '/models/[tab]',
  route: '/models/[tab]',
  asPath: '/models/aim-catalog',
};

vi.mock('next/router', () => ({
  useRouter: () => mockRouter,
}));

vi.mock('next-i18next', () => ({
  Trans: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock('@/contexts/ProjectContext', () => ({
  useProject: () => ({
    activeProject: 'test-project-123',
    setActiveProject: vi.fn(),
    projectPath: (path: string) => `/test-project-123${path}`,
  }),
}));

describe('Models Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPush.mockClear();
    mockRouter.query = { tab: 'aim-catalog' };
  });

  it('renders the models page with correct tabs', async () => {
    render(<ModelsPage />, { wrapper });

    expect(screen.getByText('tabs.aimCatalog')).toBeInTheDocument();
    expect(screen.getByText('tabs.customModels')).toBeInTheDocument();
    expect(screen.getByText('tabs.deployedModels')).toBeInTheDocument();

    expect(screen.getByTestId('aim-catalog')).toBeInTheDocument();
  });

  it('switches between tabs correctly', async () => {
    const { rerender } = render(<ModelsPage />, { wrapper });

    expect(screen.getByTestId('aim-catalog')).toBeInTheDocument();
    expect(screen.queryByTestId('custom-models')).not.toBeInTheDocument();
    expect(screen.queryByTestId('deployed-models')).not.toBeInTheDocument();

    mockRouter.query = { tab: 'custom-models' };
    rerender(<ModelsPage />);

    await waitFor(() => {
      expect(screen.getByTestId('custom-models')).toBeInTheDocument();
      expect(screen.queryByTestId('aim-catalog')).not.toBeInTheDocument();
    });

    mockRouter.query = { tab: 'deployed-models' };
    rerender(<ModelsPage />);

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
});
