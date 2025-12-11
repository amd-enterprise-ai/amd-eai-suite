// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen, act, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import FilterDropdown, {
  FilterItem,
} from '@/components/shared/Filters/FilterDropdown';

vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('FilterDropdown Component', () => {
  const mockItems: FilterItem[] = [
    { key: 'item1', label: 'Item One', description: 'First item description' },
    { key: 'item2', label: 'Item Two', description: 'Second item description' },
    {
      key: 'item3',
      label: 'Item Three',
      description: 'Third item description',
      showDivider: true,
    },
  ];

  const defaultProps = {
    label: 'Test Filter',
    items: mockItems,
  };

  it('renders correctly with default props', () => {
    render(<FilterDropdown {...defaultProps} />);
    const triggerButton = screen.getByRole('button', { name: 'Test Filter' });
    expect(triggerButton).toBeInTheDocument();
    expect(triggerButton).toHaveTextContent('Test Filter');
  });

  it('reflects external selection in the dropdown menu', async () => {
    render(<FilterDropdown {...defaultProps} selectedKeys={['item1']} />);
    const triggerButton = screen.getByRole('button', { name: 'Test Filter' });
    await userEvent.click(triggerButton);

    const item1 = await screen.findByRole('menuitemcheckbox', {
      name: 'Item One',
    });
    expect(item1).toHaveAttribute('aria-checked', 'true');
  });

  it('displays multiple selected items in the dropdown menu', async () => {
    render(
      <FilterDropdown {...defaultProps} selectedKeys={['item1', 'item2']} />,
    );
    const triggerButton = screen.getByRole('button', { name: 'Test Filter' });
    await userEvent.click(triggerButton);

    const item1 = await screen.findByRole('menuitemcheckbox', {
      name: 'Item One',
    });
    const item2 = await screen.findByRole('menuitemcheckbox', {
      name: 'Item Two',
    });
    expect(item1).toHaveAttribute('aria-checked', 'true');
    expect(item2).toHaveAttribute('aria-checked', 'true');
  });

  it('selects all items by default when no selection is provided', async () => {
    render(<FilterDropdown {...defaultProps} />);
    // No badge or reset button should be visible initially
    expect(screen.queryByRole('badge')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Reset filter' }),
    ).not.toBeInTheDocument();

    const triggerButton = screen.getByRole('button', { name: 'Test Filter' });
    await userEvent.click(triggerButton);

    const menu = await screen.findByRole('menu');
    const selectedItems = menu.querySelectorAll('[aria-checked="true"]');
    expect(selectedItems.length).toBe(3);
  });

  it('selects no items when defaultSelectedKeys is an empty array', async () => {
    render(<FilterDropdown {...defaultProps} defaultSelectedKeys={[]} />);
    const triggerButton = screen.getByRole('button', { name: 'Test Filter' });
    await userEvent.click(triggerButton);

    const menu = await screen.findByRole('menu');
    const selectedItems = menu.querySelectorAll('[aria-checked="true"]');
    expect(selectedItems.length).toBe(0);
  });

  it('shows reset button and active state after user interaction', async () => {
    render(<FilterDropdown {...defaultProps} />);
    const triggerButton = screen.getByRole('button', { name: 'Test Filter' });
    await userEvent.click(triggerButton);

    const item1 = await screen.findByRole('menuitemcheckbox', {
      name: 'Item One',
    });

    await userEvent.click(item1);

    // After clicking one item in a fully-selected list, only that item remains selected
    await waitFor(() => {
      const badge = screen.getByText('1');
      expect(badge).toBeInTheDocument();
    });

    await waitFor(() => {
      const resetButton = screen.getByLabelText('actions.clear.title');
      expect(resetButton).toBeInTheDocument();
    });
  });

  it('calls onSelectionChange and updates badge', async () => {
    const onSelectionChangeMock = vi.fn();
    render(
      <FilterDropdown
        {...defaultProps}
        onSelectionChange={onSelectionChangeMock}
      />,
    );
    const triggerButton = screen.getByRole('button', { name: 'Test Filter' });
    await userEvent.click(triggerButton);

    const item1 = await screen.findByRole('menuitemcheckbox', {
      name: 'Item One',
    });

    await userEvent.click(item1);

    await waitFor(() => {
      expect(onSelectionChangeMock).toHaveBeenCalled();
    });

    // First interaction selects only the clicked item
    expect(onSelectionChangeMock).toHaveBeenCalledWith(new Set(['item1']));

    const badge = await screen.findByText('1');
    expect(badge).toBeInTheDocument();
  });

  it('renders all provided items', async () => {
    render(<FilterDropdown {...defaultProps} />);
    const triggerButton = screen.getByRole('button', { name: 'Test Filter' });
    await userEvent.click(triggerButton);

    for (const item of mockItems) {
      const itemElement = await screen.findByText(item.label);
      expect(itemElement).toBeInTheDocument();
    }
  });

  it('applies showDivider property to dropdown items', async () => {
    render(<FilterDropdown {...defaultProps} />);
    const triggerButton = screen.getByRole('button', { name: 'Test Filter' });
    await userEvent.click(triggerButton);

    const itemWithDivider = (await screen.findByText('Item Three')).closest(
      '[role="menuitemcheckbox"]',
    );
    expect(itemWithDivider).toHaveClass('mb-1.5');

    const itemWithoutDivider = (await screen.findByText('Item One')).closest(
      '[role="menuitemcheckbox"]',
    );
    expect(itemWithoutDivider).not.toHaveClass('mb-1.5');
  });

  it('supports external control via defaultSelectedKeys', async () => {
    render(
      <FilterDropdown {...defaultProps} defaultSelectedKeys={['item2']} />,
    );
    const triggerButton = screen.getByRole('button', { name: 'Test Filter' });
    await userEvent.click(triggerButton);

    const item2 = await screen.findByRole('menuitemcheckbox', {
      name: 'Item Two',
    });
    expect(item2).toHaveAttribute('aria-checked', 'true');

    const item1 = await screen.findByRole('menuitemcheckbox', {
      name: 'Item One',
    });
    expect(item1).toHaveAttribute('aria-checked', 'false');
  });

  it('handles keyboard interactions - Space to open and Escape to close dropdown', async () => {
    render(<FilterDropdown {...defaultProps} />);
    const triggerButton = screen.getByRole('button', { name: 'Test Filter' });

    act(() => {
      triggerButton.focus();
    });
    await userEvent.keyboard('[Space]');

    const dropdownMenu = screen.getByRole('menu');
    expect(dropdownMenu).toBeInTheDocument();

    await userEvent.keyboard('[Escape]');

    await waitFor(() => {
      expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    });
  });

  it('opens dropdown with keyboard, selects second item, then closes and clear filter', async () => {
    render(<FilterDropdown {...defaultProps} />);
    const triggerButton = screen.getByRole('button', { name: 'Test Filter' });

    act(() => {
      triggerButton.focus();
    });
    await userEvent.keyboard('[Space]');

    const dropdownMenu = screen.getByRole('menu');
    expect(dropdownMenu).toBeInTheDocument();

    await userEvent.keyboard('[ArrowDown]');
    await userEvent.keyboard('[Space]');

    await userEvent.keyboard('[Escape]');

    await waitFor(() => {
      expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    });

    await waitFor(() => {
      const badge = screen.getByText('1');
      expect(badge).toBeInTheDocument();
    });

    act(() => {
      triggerButton.focus();
    });
    await userEvent.keyboard('[Tab]');
    await userEvent.keyboard('[Tab]');
    await userEvent.keyboard('[Space]');

    await waitFor(() => {
      expect(screen.queryByRole('badge')).not.toBeInTheDocument();
    });

    expect(
      screen.queryByRole('button', { name: 'Reset filter' }),
    ).not.toBeInTheDocument();
  });

  it('keyboard interaction: select and deselect items returns to default all-selected state', async () => {
    render(<FilterDropdown {...defaultProps} />);
    const triggerButton = screen.getByRole('button', { name: 'Test Filter' });

    act(() => {
      triggerButton.focus();
    });
    await userEvent.keyboard('[Space]');

    const dropdownMenu = screen.getByRole('menu');
    expect(dropdownMenu).toBeInTheDocument();

    await userEvent.keyboard('[Space]');
    await userEvent.keyboard('[ArrowDown]');
    await userEvent.keyboard('[Space]');
    await userEvent.keyboard('[Space]');
    await userEvent.keyboard('[ArrowUp]');
    await userEvent.keyboard('[Space]');

    await userEvent.keyboard('[Escape]');

    await waitFor(() => {
      expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    });

    expect(screen.queryByRole('badge')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Reset filter' }),
    ).not.toBeInTheDocument();

    await userEvent.click(triggerButton);
    const menu = await screen.findByRole('menu');
    const selectedItems = menu.querySelectorAll('[aria-checked="true"]');
    expect(selectedItems.length).toBe(3);
  });
});
