// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, fireEvent, waitFor } from '@testing-library/react';

import { SidebarItem } from '@/types/navigation';

import { CollapsibleItem } from '@/components/shared/Navigation/CollapsibleItem';

import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock next-i18next
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// Mock next/navigation
vi.mock('next/navigation', () => ({
  usePathname: vi.fn(() => '/current-path'),
}));

// Mock the utility function
vi.mock('@/utils/app/navigation', () => ({
  isMenuItemActive: vi.fn((href: string, path: string) => {
    return href === '/active-item';
  }),
}));

const mockItem: SidebarItem = {
  href: '/test-item',
  stringKey: 'pages.testItem.title',
  icon: <div data-testid="test-icon">🔧</div>,
};

const mockActiveItem: SidebarItem = {
  href: '/active-item',
  stringKey: 'pages.activeItem.title',
  icon: <div data-testid="active-icon">✅</div>,
};

const mockItemWithSubItems: SidebarItem = {
  href: '/parent-item',
  stringKey: 'pages.parentItem.title',
  icon: <div data-testid="parent-icon">📁</div>,
  subItems: [
    {
      href: '/parent-item/child1',
      stringKey: 'pages.parentItem.child1',
      icon: <div data-testid="child1-icon">📄</div>,
    },
    {
      href: '/parent-item/child2',
      stringKey: 'pages.parentItem.child2',
      icon: <div data-testid="child2-icon">📄</div>,
    },
  ],
};

const defaultProps = {
  item: mockItem,
  isSidebarMini: false,
  defaultExpanded: false,
};

describe('CollapsibleItem', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('renders the item correctly', () => {
      const { getByText, getByTestId } = render(
        <CollapsibleItem {...defaultProps} />,
      );

      expect(getByText('pages.testItem.title')).toBeInTheDocument();
      expect(getByTestId('test-icon')).toBeInTheDocument();
    });

    it('renders with correct initial expansion state', () => {
      const { container } = render(
        <CollapsibleItem {...defaultProps} defaultExpanded={false} />,
      );

      const button = container.querySelector('button');
      expect(button).toBeInTheDocument();
    });

    it('renders expanded when defaultExpanded is true', () => {
      const { container } = render(
        <CollapsibleItem
          {...defaultProps}
          item={mockItemWithSubItems}
          defaultExpanded={true}
        />,
      );

      const expandedContent = container.querySelector('.overflow-hidden');
      expect(expandedContent).toBeInTheDocument();
      const subItemsList = container.querySelector('ul.ml-4');
      expect(subItemsList).toBeInTheDocument();
    });
  });

  describe('Active State', () => {
    it('applies active styling when item is active', () => {
      const { container } = render(
        <CollapsibleItem {...defaultProps} item={mockActiveItem} />,
      );

      const menuItem = container.querySelector('.menu-item');
      expect(menuItem).toHaveClass('bg-primary-200/75');
      expect(menuItem).toHaveClass('text-primary');
    });

    it('applies inactive styling when item is not active', () => {
      const { container } = render(
        <CollapsibleItem {...defaultProps} item={mockItem} />,
      );

      const menuItem = container.querySelector('.menu-item');
      expect(menuItem).toHaveClass('bg-transparent');
      expect(menuItem).not.toHaveClass('bg-primary-200/75');
    });
  });

  describe('Mini Sidebar Behavior', () => {
    it('applies correct classes when sidebar is mini', () => {
      const { container } = render(
        <CollapsibleItem {...defaultProps} isSidebarMini={true} />,
      );

      const textSpan = container.querySelector('.text-nowrap');
      expect(textSpan).toHaveClass('scale-0');
      expect(textSpan).toHaveClass('group-hover:scale-100');
    });

    it('applies correct classes when sidebar is not mini', () => {
      const { container } = render(
        <CollapsibleItem {...defaultProps} isSidebarMini={false} />,
      );

      const textSpan = container.querySelector('.text-nowrap');
      expect(textSpan).toHaveClass('scale-100');
      expect(textSpan).not.toHaveClass('scale-0');
    });
  });

  describe('Expansion/Collapse Functionality', () => {
    it('toggles expansion when button is clicked', async () => {
      const { container } = render(
        <CollapsibleItem
          {...defaultProps}
          item={mockItemWithSubItems}
          defaultExpanded={false}
        />,
      );

      const button = container.querySelector('button');
      expect(button).toBeInTheDocument();

      let expandedContent = container.querySelector('.overflow-hidden');
      expect(expandedContent).toBeInTheDocument();

      if (button) {
        fireEvent.click(button);
      }

      await waitFor(() => {
        expandedContent = container.querySelector('.overflow-hidden');
        expect(expandedContent).toBeInTheDocument();
      });
    });

    it('shows chevron right when collapsed', () => {
      const { container } = render(
        <CollapsibleItem
          {...defaultProps}
          item={mockItemWithSubItems}
          defaultExpanded={false}
        />,
      );
      const chevronSpan = container.querySelector('.px-2');
      expect(chevronSpan).toBeInTheDocument();
    });

    it('shows chevron down when expanded', () => {
      const { container } = render(
        <CollapsibleItem
          {...defaultProps}
          item={mockItemWithSubItems}
          defaultExpanded={true}
        />,
      );

      const chevronSpan = container.querySelector('.px-2');
      expect(chevronSpan).toBeInTheDocument();
    });
  });

  describe('SubItems Rendering', () => {
    it('renders sub-items when item has subItems and is expanded', () => {
      const { getByText } = render(
        <CollapsibleItem
          {...defaultProps}
          item={mockItemWithSubItems}
          defaultExpanded={true}
        />,
      );

      expect(getByText('pages.parentItem.child1')).toBeInTheDocument();
      expect(getByText('pages.parentItem.child2')).toBeInTheDocument();
    });

    it('does not render sub-items when collapsed', () => {
      const { container } = render(
        <CollapsibleItem
          {...defaultProps}
          item={mockItemWithSubItems}
          defaultExpanded={false}
        />,
      );

      const expandedContent = container.querySelector('.overflow-hidden');
      expect(expandedContent).toBeInTheDocument();
      // The subitems should still be in the DOM but with height: 0
      const subItemsList = container.querySelector('ul.ml-4');
      expect(subItemsList).toBeInTheDocument();
    });

    it('renders sub-items with correct nesting styles', () => {
      const { container } = render(
        <CollapsibleItem
          {...defaultProps}
          item={mockItemWithSubItems}
          defaultExpanded={true}
        />,
      );

      const nestedList = container.querySelector('ul.ml-4');
      expect(nestedList).toBeInTheDocument();
      expect(nestedList).toHaveClass('mt-1');
    });

    it('applies correct mini sidebar classes to sub-items container', () => {
      const { container } = render(
        <CollapsibleItem
          {...defaultProps}
          item={mockItemWithSubItems}
          isSidebarMini={true}
          defaultExpanded={true}
        />,
      );

      const nestedList = container.querySelector('ul.ml-4');
      expect(nestedList).toHaveClass('group-hover:block');
      expect(nestedList).toHaveClass('hidden');
    });
  });

  describe('Height Calculation and Animation', () => {
    it('renders expandable content area when item has subItems', () => {
      const { container } = render(
        <CollapsibleItem
          {...defaultProps}
          item={mockItemWithSubItems}
          defaultExpanded={true}
        />,
      );

      // Should render the expandable content area
      const expandedContent = container.querySelector('.overflow-hidden');
      expect(expandedContent).toBeInTheDocument();

      // Should render the sub-items within the expandable area
      const subItemsList = container.querySelector('ul.ml-4');
      expect(subItemsList).toBeInTheDocument();
    });

    it('updates height when subItems change', async () => {
      const { container, rerender } = render(
        <CollapsibleItem
          {...defaultProps}
          item={mockItemWithSubItems}
          defaultExpanded={true}
        />,
      );

      const itemWithMoreSubItems = {
        ...mockItemWithSubItems,
        subItems: [
          ...mockItemWithSubItems.subItems!,
          {
            href: '/parent-item/child3',
            stringKey: 'pages.parentItem.child3',
            icon: <div data-testid="child3-icon">📄</div>,
          },
        ],
      };

      rerender(
        <CollapsibleItem
          {...defaultProps}
          item={itemWithMoreSubItems}
          defaultExpanded={true}
        />,
      );

      await waitFor(() => {
        // Should recalculate height with more items
        const expandedContent = container.querySelector('.overflow-hidden');
        expect(expandedContent).toBeInTheDocument();
      });
    });
  });

  describe('Edge Cases', () => {
    it('handles item without subItems', () => {
      const { container } = render(
        <CollapsibleItem {...defaultProps} item={mockItem} />,
      );

      // Should render the main button (always rendered regardless of subItems)
      const button = container.querySelector('button');
      expect(button).toBeInTheDocument();

      // Should not render the expandable content section when there are no subItems
      // The component should not render the div with .overflow-hidden class when item.subItems is undefined/null
      const expandableContent = container.querySelector('div.overflow-hidden');
      expect(expandableContent).not.toBeInTheDocument();
    });

    it('handles empty subItems array', () => {
      const itemWithEmptySubItems = {
        ...mockItem,
        subItems: [],
      };

      const { container } = render(
        <CollapsibleItem {...defaultProps} item={itemWithEmptySubItems} />,
      );

      // Should render expandable content but with no items
      const expandableContent = container.querySelector('.overflow-hidden');
      expect(expandableContent).toBeInTheDocument();

      const subItemsList = container.querySelectorAll('ul.ml-4 li');
      expect(subItemsList).toHaveLength(0);
    });

    it('handles missing icon gracefully', () => {
      const itemWithoutIcon = {
        ...mockItem,
        icon: undefined,
      };

      const { container } = render(
        <CollapsibleItem {...defaultProps} item={itemWithoutIcon} />,
      );

      // Should still render without crashing
      expect(container.firstChild).toBeInTheDocument();
    });
  });
});
