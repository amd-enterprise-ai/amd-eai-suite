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

import { getAims } from '@/services/app/aims';

import AIMCatalog from '@/components/features/models/AIMCatalog';

import wrapper from '@/__tests__/ProviderWrapper';
import { Mock, vi } from 'vitest';
import { mockAims } from '@/__mocks__/services/app/aims.data';

// Mock the API services
vi.mock('@/services/app/aims', () => ({
  getAims: vi.fn(),
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

// Mock useRouter
vi.mock('next/router', () => ({
  useRouter: vi.fn(),
}));

// Mock ModelIcon to avoid SVG loading issues
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

// Mock ProjectContext
vi.mock('@/contexts/ProjectContext', () => ({
  useProject: () => ({
    activeProject: 'test-project-1',
    projects: [{ id: 'test-project-1', name: 'Test Project' }],
  }),
}));

describe('AIM Catalog', () => {
  const mockPush = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useRouter as Mock).mockReturnValue({
      push: mockPush,
      pathname: '/models',
      query: {},
    });
    (getAims as Mock).mockResolvedValue(mockAims);
  });

  it('renders AIM catalog component', async () => {
    await act(async () => {
      render(<AIMCatalog />, {
        wrapper,
      });
    });

    await waitFor(() => {
      expect(getAims).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText('Llama 2 7B')).toBeInTheDocument();
      expect(screen.getByText('Stable Diffusion XL')).toBeInTheDocument();
      expect(screen.getByText('Vision Detection Model')).toBeInTheDocument();
    });
  });

  it('shows loading state', async () => {
    (getAims as Mock).mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 1000)),
    );

    render(<AIMCatalog />, {
      wrapper,
    });

    expect(screen.getByTestId('aim-catalog-loading')).toBeInTheDocument();
  });

  it('filters AIMs by search query', async () => {
    await act(async () => {
      render(<AIMCatalog />, {
        wrapper,
      });
    });

    await waitFor(() => {
      expect(getAims).toHaveBeenCalled();
    });

    const searchInput = screen.getByPlaceholderText(
      'list.filter.search.placeholder',
    );
    fireEvent.change(searchInput, { target: { value: 'Llama' } });

    await waitFor(() => {
      expect(screen.getByText('Llama 2 7B')).toBeInTheDocument();
      expect(screen.queryByText('Stable Diffusion XL')).not.toBeInTheDocument();
      expect(
        screen.queryByText('Vision Detection Model'),
      ).not.toBeInTheDocument();
    });
  });

  it('filters AIMs by tag', async () => {
    await act(async () => {
      render(<AIMCatalog />, {
        wrapper,
      });
    });

    await waitFor(() => {
      expect(getAims).toHaveBeenCalled();
    });

    // Verify the tag filter is available
    const tagSelect = screen.getByLabelText('list.filter.tag.placeholder');
    expect(tagSelect).toBeInTheDocument();
  });

  it('clears filters when clear button is clicked', async () => {
    await act(async () => {
      render(<AIMCatalog />, {
        wrapper,
      });
    });

    await waitFor(() => {
      expect(getAims).toHaveBeenCalled();
    });

    const searchInput = screen.getByPlaceholderText(
      'list.filter.search.placeholder',
    );
    fireEvent.change(searchInput, { target: { value: 'Llama' } });

    await waitFor(() => {
      const clearButton = screen.getByText('actions.clearFilters.title');
      expect(clearButton).not.toBeDisabled();
    });

    const clearButton = screen.getByText('actions.clearFilters.title');
    await act(async () => {
      fireEvent.click(clearButton);
    });

    await waitFor(() => {
      expect(searchInput).toHaveValue('');
    });
  });

  it('shows empty state when no AIMs match filters', async () => {
    (getAims as Mock).mockResolvedValue([]);

    await act(async () => {
      render(<AIMCatalog />, {
        wrapper,
      });
    });

    await waitFor(() => {
      expect(getAims).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText('list.empty.description')).toBeInTheDocument();
    });
  });

  it('handles API errors gracefully', async () => {
    const mockError = new Error('API Error');
    (getAims as Mock).mockRejectedValue(mockError);

    await act(async () => {
      render(<AIMCatalog />, {
        wrapper,
      });
    });

    await waitFor(() => {
      expect(getAims).toHaveBeenCalled();
    });
  });

  it('filters out deleted AIMs from catalog', async () => {
    (getAims as Mock).mockResolvedValue(mockAims);

    await act(async () => {
      render(<AIMCatalog />, {
        wrapper,
      });
    });

    await waitFor(() => {
      expect(getAims).toHaveBeenCalled();
    });

    await waitFor(() => {
      // Should show non-deleted AIMs
      expect(screen.getByText('Llama 2 7B')).toBeInTheDocument();
      expect(screen.getByText('Stable Diffusion XL')).toBeInTheDocument();
      expect(screen.getByText('Vision Detection Model')).toBeInTheDocument();

      // Should NOT show deleted AIM
      expect(screen.queryByText('Deleted Old Model')).not.toBeInTheDocument();
    });
  });
});
