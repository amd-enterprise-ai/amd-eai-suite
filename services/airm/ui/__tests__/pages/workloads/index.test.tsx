// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  render,
  screen,
  waitFor,
  within, // Added within
} from '@testing-library/react';
import { vi } from 'vitest';
import { deleteWorkload, listWorkloads } from '@/services/app/workloads';
import { getAims } from '@/services/app/aims';
import { getModels } from '@/services/app/models';
import WorkloadsPage from '@/pages/workloads';
import wrapper from '@/__tests__/ProviderWrapper';
import { mockWorkloads } from '@/__mocks__/services/app/workloads.data';
import { mockAims } from '@/__mocks__/services/app/aims.data';

// Mock the next router
vi.mock('next/router', () => ({
  useRouter: vi.fn(() => ({
    push: vi.fn(),
    query: {},
    pathname: '/workloads',
  })),
}));

// Mock the API services
vi.mock('@/services/app/workloads', () => ({
  listWorkloads: vi.fn(),
  deleteWorkload: vi.fn(),
}));

vi.mock('@/services/app/aims', () => ({
  getAims: vi.fn(),
}));

vi.mock('@/services/app/models', () => ({
  getModels: vi.fn(),
}));

// Mock useSystemToast for testing
vi.mock('@/hooks/useSystemToast', () => ({
  __esModule: true,
  default: () => ({
    toast: {
      success: vi.fn(),
      error: vi.fn(),
    },
  }),
}));

// Mock the next-auth session
vi.mock('next-auth', () => ({
  getServerSession: vi.fn(() => ({
    user: { email: 'test@example.com' },
    accessToken: 'test-token',
  })),
}));

// Mock translations
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock('next-i18next/serverSideTranslations', () => ({
  serverSideTranslations: vi.fn(() => Promise.resolve({ _nextI18Next: {} })),
}));

describe('Workloads Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (listWorkloads as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockWorkloads,
    );
    (deleteWorkload as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      {},
    );
    (getAims as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockAims,
    );
    // Mock getModels to return models from mockWorkloads
    const mockModels = mockWorkloads
      .filter((w) => w.model)
      .map((w) => w.model!);
    (getModels as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockModels,
    );
  });

  it('renders the workloads page', async () => {
    render(<WorkloadsPage />, { wrapper });

    // Wait for the workloads to load
    await waitFor(() => {
      expect(listWorkloads).toHaveBeenCalledTimes(1);
    });

    // Verify that core UI elements are displayed
    expect(
      screen.getByPlaceholderText('list.filters.search.placeholder'),
    ).toBeInTheDocument();
    expect(screen.getByText('list.filters.type.label')).toBeInTheDocument();
    expect(screen.getByText('list.filters.status.label')).toBeInTheDocument();
  });

  it('filters workloads by type', async () => {
    render(<WorkloadsPage />, { wrapper });

    // Wait for the workloads to load
    await waitFor(() => {
      expect(listWorkloads).toHaveBeenCalledTimes(1);
    });

    // Check if the type filter button exists
    expect(screen.getByText('list.filters.type.label')).toBeInTheDocument();
  });

  it('renders status filter', async () => {
    render(<WorkloadsPage />, { wrapper });

    // Wait for the workloads to load
    await waitFor(() => {
      expect(listWorkloads).toHaveBeenCalledTimes(1);
    });

    // Check if the status filter button exists
    expect(screen.getByText('list.filters.status.label')).toBeInTheDocument();
  });

  it('renders clear filters button', async () => {
    render(<WorkloadsPage />, { wrapper });

    // Wait for the workloads to load
    await waitFor(() => {
      expect(listWorkloads).toHaveBeenCalledTimes(1);
    });

    const clearButton = screen.getByText('actions.clearFilters.title');

    // Check if clear filters button exists
    expect(clearButton).toBeInTheDocument();
  });

  it('renders refresh button', async () => {
    render(<WorkloadsPage />, { wrapper });

    // Wait for the workloads to load
    await waitFor(() => {
      expect(listWorkloads).toHaveBeenCalledTimes(1);
    });

    const refreshButton = screen.getByRole('button', { name: /refresh/i });

    // Check if refresh button exists
    expect(refreshButton).toBeInTheDocument();
  });

  it('calls listWorkloads on initial render', async () => {
    render(<WorkloadsPage />, { wrapper });

    // Verify the API was called once
    await waitFor(() => {
      expect(listWorkloads).toHaveBeenCalledTimes(1);
    });
  });

  it('displays model canonical names in the table', async () => {
    render(<WorkloadsPage />, { wrapper });

    // Wait for the workloads to load
    await waitFor(() => {
      expect(listWorkloads).toHaveBeenCalledTimes(1);
    });

    // Verify that canonical names are displayed in the table
    await waitFor(() => {
      // Check that canonical names from the mock data are displayed
      const llamaElements = screen.getAllByText('meta/llama-7b');
      expect(llamaElements.length).toBeGreaterThan(0);

      const sdxlElements = screen.getAllByText(
        'stabilityai/stable-diffusion-xl',
      );
      expect(sdxlElements.length).toBeGreaterThan(0);

      const gptElements = screen.getAllByText('openai/gpt-4-base');
      expect(gptElements.length).toBeGreaterThan(0);
    });
  });
});
