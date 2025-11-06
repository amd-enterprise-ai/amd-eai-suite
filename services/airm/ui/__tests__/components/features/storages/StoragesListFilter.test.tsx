// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { StorageScope, StorageType } from '@/types/enums/storages';

import { StoragesListFilter } from '@/components/features/storages';

describe('StoragesListFilter', () => {
  it('renders StoragesListFilter with correct filters', () => {
    const onFilterChange = vi.fn();
    render(<StoragesListFilter onFilterChange={onFilterChange} />);
    expect(
      screen.getByPlaceholderText('list.filter.search.placeholder'),
    ).toBeInTheDocument();

    expect(
      screen.getByRole('button', { name: 'actions.clearFilters.title' }),
    ).toBeInTheDocument();
  });

  it('can clear filters', async () => {
    const onFilterChange = vi.fn();
    render(<StoragesListFilter onFilterChange={onFilterChange} />);

    // Then change search input
    const searchInput = screen.getByPlaceholderText(
      'list.filter.search.placeholder',
    );
    fireEvent.change(searchInput, { target: { value: 'searchValue' } });

    await waitFor(() => {
      expect(onFilterChange).toHaveBeenCalledWith({
        search: ['searchValue'],
      });
    });

    fireEvent.click(screen.getByText('actions.clearFilters.title'));

    await waitFor(() => {
      expect(onFilterChange).toHaveBeenCalledWith({});
    });
  });

  it('if in project scope do not show scope filter', async () => {
    const onFilterChange = vi.fn();
    render(<StoragesListFilter onFilterChange={onFilterChange} isInProjects />);

    const searchInput = screen.getByPlaceholderText(
      'list.filter.search.placeholder',
    );
    await fireEvent.change(searchInput, { target: { value: 'searchValue' } });

    const scopeButton = screen.queryByRole('button', {
      name: 'list.filter.scope.label',
    });
    expect(scopeButton).not.toBeInTheDocument();
  });
});
