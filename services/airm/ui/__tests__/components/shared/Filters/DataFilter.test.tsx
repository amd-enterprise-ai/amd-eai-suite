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
import React from 'react';

import { FilterComponentType } from '@/types/enums/filters';

import { DataFilter } from '@/components/shared/Filters/DataFilter';

import { beforeEach, describe, expect, it, vi } from 'vitest';

// Mock next-i18next
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('DataFilter', () => {
  const filters = {
    name: {
      name: 'name',
      type: FilterComponentType.TEXT,
      placeholder: 'Enter name',
      className: 'name-input',
      label: 'Name',
    },
    status: {
      name: 'status',
      type: FilterComponentType.DROPDOWN,
      label: 'Status',
      className: 'status-select',
      icon: <span>icon</span>,
      fields: [
        { key: 'active', label: 'Active' },
        { key: 'inactive', label: 'Inactive' },
      ],
    },
  };

  let onFilterChange: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onFilterChange = vi.fn();
  });

  it('renders text and select filters', () => {
    render(<DataFilter filters={filters} onFilterChange={onFilterChange} />);
    expect(screen.getByPlaceholderText('Enter name')).toBeInTheDocument();
    expect(screen.getByLabelText('Status')).toBeInTheDocument();
  });

  it('calls onFilterChange when text input changes', async () => {
    await act(async () => {
      render(<DataFilter filters={filters} onFilterChange={onFilterChange} />);
    });
    const input = screen.getByPlaceholderText('Enter name');
    fireEvent.change(input, { target: { value: 'John' } });
    await waitFor(() => {
      expect(onFilterChange).toHaveBeenCalledWith({ name: ['John'] });
    });
  });

  it('calls onFilterChange when select changes', async () => {
    await act(async () => {
      render(<DataFilter filters={filters} onFilterChange={onFilterChange} />);
    });

    const selectTrigger = screen.getByRole('button', { name: 'Status' });
    await fireEvent.click(selectTrigger);

    // First click on Active - this will be the only selection due to "first interaction" behavior
    const activeOption = screen.getByText('Active');
    await fireEvent.click(activeOption);

    // The first interaction will only select the clicked item
    await waitFor(() => {
      expect(onFilterChange).toHaveBeenCalledWith({
        status: ['active'],
      });
    });

    // Second click on Inactive should add it to the selection
    const inactiveOption = screen.getByText('Inactive');
    await fireEvent.click(inactiveOption);

    await waitFor(() => {
      expect(onFilterChange).toHaveBeenCalledWith({
        status: ['active', 'inactive'],
      });
    });
  });

  it('calls onFilterChange when select changes and text changes', async () => {
    await act(async () => {
      render(<DataFilter filters={filters} onFilterChange={onFilterChange} />);
    });

    const input = screen.getByPlaceholderText('Enter name');
    fireEvent.change(input, { target: { value: 'John' } });

    // Wait for the input change to be processed first
    await waitFor(() => {
      expect(onFilterChange).toHaveBeenCalledWith({
        name: ['John'],
      });
    });

    const selectTrigger = screen.getByRole('button', { name: 'Status' });
    await fireEvent.click(selectTrigger);

    // First click on Active - this will be the only selection due to "first interaction" behavior
    const activeOption = screen.getByText('Active');
    await fireEvent.click(activeOption);

    // The first interaction will only select the clicked item
    await waitFor(() => {
      expect(onFilterChange).toHaveBeenCalledWith({
        name: ['John'],
        status: ['active'],
      });
    });

    // Second click on Inactive should add it to the selection
    const inactiveOption = screen.getByText('Inactive');
    await fireEvent.click(inactiveOption);

    await waitFor(() => {
      expect(onFilterChange).toHaveBeenCalledWith({
        name: ['John'],
        status: ['active', 'inactive'],
      });
    });
  });

  it('clears filters and calls onFilterChange with empty object', async () => {
    await act(async () => {
      render(
        <DataFilter
          filters={filters}
          onFilterChange={onFilterChange}
          canClear
        />,
      );
    });

    const input = screen.getByPlaceholderText('Enter name');
    fireEvent.change(input, { target: { value: 'John' } });

    // Wait for the name filter to be set first
    await waitFor(() => {
      expect(onFilterChange).toHaveBeenCalledWith({
        name: ['John'],
      });
    });

    const selectTrigger = screen.getByRole('button', { name: 'Status' });
    await fireEvent.click(selectTrigger);
    const activeOption = screen.getByText('Active');
    await fireEvent.click(activeOption);

    // Due to the "first interaction" behavior, the first click will replace any existing selections
    // and only select the clicked item
    await waitFor(() => {
      expect(onFilterChange).toHaveBeenCalledWith({
        name: ['John'],
        status: ['active'],
      });
    });

    const clearBtn = screen.getByLabelText('actions.clearFilters.title');
    await fireEvent.click(clearBtn);

    await waitFor(() => {
      expect(onFilterChange).toHaveBeenCalledWith({});
    });

    expect(input).toHaveValue('');
  });

  it('does not render clear button if canClear is false', () => {
    act(() => {
      render(
        <DataFilter
          filters={filters}
          onFilterChange={onFilterChange}
          canClear={false}
        />,
      );
    });

    expect(screen.queryByLabelText('actions.clearFilters.title')).toBeNull();
  });

  it('does not render clear button if no filters', async () => {
    await act(async () => {
      render(
        <DataFilter filters={{}} onFilterChange={onFilterChange} canClear />,
      );
    });
    expect(screen.queryByLabelText('actions.clearFilters.title')).toBeNull();
  });
});
