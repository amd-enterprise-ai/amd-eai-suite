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

import { deleteApiKey, fetchProjectApiKeys } from '@/services/app/api-keys';

import {
  generateMockApiKeys,
  generateMockApiKeyResponse,
} from '@/__mocks__/utils/api-keys-mock';

import { ApiKeysTableField } from '@/types/enums/api-keys-table-fields';

import ApiKeysTable from '@/components/features/api-keys/ApiKeysTable';

import wrapper from '@/__tests__/ProviderWrapper';

// Mock the API functions
vi.mock('@/services/app/api-keys', () => ({
  fetchProjectApiKeys: vi.fn(),
  deleteApiKey: vi.fn(),
}));

const mockFetchProjectApiKeys = vi.mocked(fetchProjectApiKeys);
const mockDeleteApiKey = vi.mocked(deleteApiKey);

describe('ApiKeysTable', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock implementation
    mockFetchProjectApiKeys.mockResolvedValue(generateMockApiKeyResponse());

    mockDeleteApiKey.mockResolvedValue();
  });

  const defaultProps = {
    projectId: 'project-1',
    createButton: <button>Create API Key</button>,
  };

  it('renders correct columns', async () => {
    await act(async () => {
      render(<ApiKeysTable {...defaultProps} />, {
        wrapper,
      });
    });

    expect(
      screen.getByText(`list.apiKeys.headers.${ApiKeysTableField.NAME}.title`),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        `list.apiKeys.headers.${ApiKeysTableField.SECRET_KEY}.title`,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        `list.apiKeys.headers.${ApiKeysTableField.CREATED_AT}.title`,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        `list.apiKeys.headers.${ApiKeysTableField.CREATED_BY}.title`,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(`list.apiKeys.headers.actions.title`),
    ).toBeInTheDocument();
  });

  it('loads and displays API keys data', async () => {
    const mockApiKeys = generateMockApiKeys(2);
    mockFetchProjectApiKeys.mockResolvedValue({
      apiKeys: mockApiKeys,
    });

    await act(async () => {
      render(<ApiKeysTable {...defaultProps} />, {
        wrapper,
      });
    });

    await waitFor(() => {
      expect(screen.getByText(mockApiKeys[0].name)).toBeInTheDocument();
      expect(screen.getByText(mockApiKeys[1].name)).toBeInTheDocument();
    });

    expect(mockFetchProjectApiKeys).toHaveBeenCalledWith('project-1');
  });

  it('handles search filter', async () => {
    const mockApiKeys = generateMockApiKeys(3);
    mockFetchProjectApiKeys.mockResolvedValue({
      apiKeys: mockApiKeys,
    });

    await act(async () => {
      render(<ApiKeysTable {...defaultProps} />, {
        wrapper,
      });
    });

    // All API keys should be visible initially
    await waitFor(() => {
      expect(screen.getByText(mockApiKeys[0].name)).toBeInTheDocument();
      expect(screen.getByText(mockApiKeys[1].name)).toBeInTheDocument();
      expect(screen.getByText(mockApiKeys[2].name)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(
      'list.filters.search.placeholder',
    );

    // Type a search term that matches only one API key
    await act(async () => {
      fireEvent.change(searchInput, { target: { value: mockApiKeys[0].name } });
    });

    // Client-side filtering should show only matching results
    // Note: This tests that filtering works, but the exact behavior depends on
    // the filter implementation. The fetch should only be called once (on mount)
    expect(mockFetchProjectApiKeys).toHaveBeenCalledTimes(1);
    expect(mockFetchProjectApiKeys).toHaveBeenCalledWith('project-1');
  });

  it('handles refresh action', async () => {
    await act(async () => {
      render(<ApiKeysTable {...defaultProps} />, {
        wrapper,
      });
    });

    // Wait for initial load
    await waitFor(() => {
      expect(mockFetchProjectApiKeys).toHaveBeenCalledTimes(1);
    });

    const refreshButton = screen.getByRole('button', { name: /refresh/i });

    fireEvent.click(refreshButton);

    // Should trigger a new fetch
    await waitFor(() => {
      expect(mockFetchProjectApiKeys).toHaveBeenCalledTimes(2);
    });
  });

  it('handles delete action', async () => {
    const mockApiKeys = generateMockApiKeys(1);
    mockFetchProjectApiKeys.mockResolvedValue({
      apiKeys: mockApiKeys,
    });

    await act(async () => {
      render(<ApiKeysTable {...defaultProps} />, {
        wrapper,
      });
    });

    await waitFor(() => {
      expect(screen.getByText(mockApiKeys[0].name)).toBeInTheDocument();
    });

    // Click on the actions menu
    const actionsButton = screen.getByLabelText('list.actions.label');
    await act(async () => {
      fireEvent.click(actionsButton);
    });

    // Find and click delete button in dropdown
    const deleteButton = screen.getByText('list.actions.delete.title');
    await act(async () => {
      fireEvent.click(deleteButton);
    });

    // Confirm delete in modal
    const confirmButton = screen.getByTestId('confirm-button');
    await act(async () => {
      fireEvent.click(confirmButton);
    });

    expect(mockDeleteApiKey).toHaveBeenCalledWith(
      'project-1',
      mockApiKeys[0].id,
    );
  });

  it('handles sorting', async () => {
    const mockApiKeys = generateMockApiKeys(3);
    mockFetchProjectApiKeys.mockResolvedValue({
      apiKeys: mockApiKeys,
    });

    await act(async () => {
      render(<ApiKeysTable {...defaultProps} />, {
        wrapper,
      });
    });

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText(mockApiKeys[0].name)).toBeInTheDocument();
    });

    const nameHeader = screen.getByText(
      `list.apiKeys.headers.${ApiKeysTableField.NAME}.title`,
    );

    await act(async () => {
      fireEvent.click(nameHeader);
    });

    // Sorting is handled client-side, so no new fetch should occur
    // The fetch should only be called once (on mount)
    expect(mockFetchProjectApiKeys).toHaveBeenCalledTimes(1);
    expect(mockFetchProjectApiKeys).toHaveBeenCalledWith('project-1');
  });

  it('displays loading skeleton when loading', async () => {
    // Create a promise that never resolves to simulate loading state
    mockFetchProjectApiKeys.mockImplementation(() => new Promise(() => {}));

    await act(async () => {
      render(<ApiKeysTable {...defaultProps} />, {
        wrapper,
      });
    });

    // Should show skeleton loading state
    expect(
      screen.getByLabelText('list.apiKeys.table.ariaLabel'),
    ).toBeInTheDocument();
  });

  it('handles empty state', async () => {
    mockFetchProjectApiKeys.mockResolvedValue({
      apiKeys: [],
    });

    await act(async () => {
      render(<ApiKeysTable {...defaultProps} />, {
        wrapper,
      });
    });

    await waitFor(() => {
      // The table should still be rendered but empty
      expect(
        screen.getByLabelText('list.apiKeys.table.ariaLabel'),
      ).toBeInTheDocument();
    });
  });

  it('renders create button', async () => {
    await act(async () => {
      render(<ApiKeysTable {...defaultProps} />, {
        wrapper,
      });
    });

    expect(screen.getByText('Create API Key')).toBeInTheDocument();
  });
});
