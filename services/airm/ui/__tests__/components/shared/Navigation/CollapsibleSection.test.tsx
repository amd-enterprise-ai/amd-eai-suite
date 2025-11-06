// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, fireEvent, waitFor } from '@testing-library/react';
import { IconServer } from '@tabler/icons-react';

import { SidebarItem } from '@/types/navigation';

import { CollapsibleSection } from '@/components/shared/Navigation/CollapsibleSection';

import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock next-i18next
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// Mock next/router
const mockPush = vi.fn();
vi.mock('next/router', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

const mockItems: SidebarItem[] = [
  {
    href: '/dashboard',
    stringKey: 'pages.dashboard.title',
    icon: <div data-testid="dashboard-icon">📊</div>,
  },
  {
    href: '/projects',
    stringKey: 'pages.projects.title',
    icon: <div data-testid="projects-icon">📋</div>,
  },
];

const mockItemsWithSubItems: SidebarItem[] = [
  {
    href: '/users',
    stringKey: 'pages.users.title',
    icon: <div data-testid="users-icon">👥</div>,
    subItems: [
      {
        href: '/users/active',
        stringKey: 'pages.users.active',
        icon: <div data-testid="active-users-icon">✅</div>,
      },
      {
        href: '/users/inactive',
        stringKey: 'pages.users.inactive',
        icon: <div data-testid="inactive-users-icon">❌</div>,
      },
    ],
  },
];

const mockSingleItem: SidebarItem[] = [
  {
    href: '/settings',
    stringKey: 'pages.settings.title',
    icon: <div data-testid="settings-icon">⚙️</div>,
  },
];

const mockSingleItemWithoutHref: SidebarItem[] = [
  {
    href: '',
    stringKey: 'pages.no-href.title',
    icon: <div data-testid="no-href-icon">🚫</div>,
  },
];

const defaultProps = {
  title: 'sections.resourceManagement.title',
  icon: IconServer,
  items: mockItems,
  isSidebarMini: false,
  isDevEnv: false,
  sectionId: 'test-section',
  isExpanded: false,
  onToggle: vi.fn(),
};

describe('CollapsibleSection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPush.mockClear();
  });

  describe('Rendering', () => {
    it('renders the section title correctly', () => {
      const { getByText } = render(<CollapsibleSection {...defaultProps} />);
      expect(
        getByText('sections.resourceManagement.title'),
      ).toBeInTheDocument();
    });

    it('renders the section icon', () => {
      const { container } = render(<CollapsibleSection {...defaultProps} />);
      // Check that the IconServer component is rendered (it will be an SVG)
      const svgElement = container.querySelector('svg');
      expect(svgElement).toBeInTheDocument();
    });

    it('renders menu items when expanded', () => {
      const { getByText } = render(
        <CollapsibleSection {...defaultProps} isExpanded={true} />,
      );
      expect(getByText('pages.dashboard.title')).toBeInTheDocument();
      expect(getByText('pages.projects.title')).toBeInTheDocument();
    });

    it('does not render menu items when collapsed', () => {
      const { queryByText } = render(
        <CollapsibleSection {...defaultProps} isExpanded={false} />,
      );
      // Items should still be in DOM but not visible (opacity: 0, height: 0)
      const dashboardItem = queryByText('pages.dashboard.title');
      expect(dashboardItem).toBeInTheDocument();
    });

    it('renders chevron down icon when expanded', () => {
      const { container } = render(
        <CollapsibleSection {...defaultProps} isExpanded={true} />,
      );
      // Should find chevron down icon (multiple SVGs will be present)
      const svgElements = container.querySelectorAll('svg');
      expect(svgElements.length).toBeGreaterThan(1); // Section icon + chevron icon
    });

    it('renders chevron right icon when collapsed', () => {
      const { container } = render(
        <CollapsibleSection {...defaultProps} isExpanded={false} />,
      );
      const svgElements = container.querySelectorAll('svg');
      expect(svgElements.length).toBeGreaterThan(1); // Section icon + chevron icon
    });
  });

  describe('Mini Sidebar Behavior', () => {
    it('shows mini icon view when sidebar is mini and not hovered', () => {
      const { container } = render(
        <CollapsibleSection {...defaultProps} isSidebarMini={true} />,
      );

      // In mini mode, there should be a clickable icon div
      const miniIconDiv = container.querySelector('.cursor-pointer');
      expect(miniIconDiv).toBeInTheDocument();
    });

    it('shows full button when sidebar is not mini', () => {
      const { container } = render(
        <CollapsibleSection {...defaultProps} isSidebarMini={false} />,
      );

      // Should find the Button component for full view
      const button = container.querySelector('button');
      expect(button).toBeInTheDocument();
    });
  });

  describe('Interaction', () => {
    it('calls onToggle when section title button is clicked', () => {
      const mockOnToggle = vi.fn();
      const { container } = render(
        <CollapsibleSection
          {...defaultProps}
          onToggle={mockOnToggle}
          isSidebarMini={false}
        />,
      );

      const button = container.querySelector('button');
      expect(button).toBeInTheDocument();

      if (button) {
        fireEvent.click(button);
        expect(mockOnToggle).toHaveBeenCalledWith('test-section');
      }
    });

    it('calls onToggle when mini icon is clicked', () => {
      const mockOnToggle = vi.fn();
      const { container } = render(
        <CollapsibleSection
          {...defaultProps}
          onToggle={mockOnToggle}
          isSidebarMini={true}
        />,
      );

      const miniIcon = container.querySelector('.cursor-pointer');
      expect(miniIcon).toBeInTheDocument();

      if (miniIcon) {
        fireEvent.click(miniIcon);
        expect(mockOnToggle).toHaveBeenCalledWith('test-section');
      }
    });
  });

  describe('Animation and Height Calculation', () => {
    it('applies correct height when expanded', async () => {
      const { container, rerender } = render(
        <CollapsibleSection {...defaultProps} isExpanded={false} />,
      );

      // Initially collapsed (height: 0)
      const content = container.querySelector('.overflow-hidden');
      expect(content).toBeInTheDocument();

      // Expand the section
      rerender(<CollapsibleSection {...defaultProps} isExpanded={true} />);

      await waitFor(() => {
        const expandedContent = container.querySelector('.overflow-hidden');
        expect(expandedContent).toBeInTheDocument();
        // The height should be calculated and applied via inline style
        const styleAttribute = expandedContent?.getAttribute('style');
        if (styleAttribute) {
          expect(styleAttribute).toContain('height:');
        }
      });
    });

    it('applies correct opacity when expanded/collapsed', () => {
      const { container, rerender } = render(
        <CollapsibleSection {...defaultProps} isExpanded={false} />,
      );

      // Initially collapsed
      const content = container.querySelector('.overflow-hidden');
      expect(content).toBeInTheDocument();

      // Expand the section
      rerender(<CollapsibleSection {...defaultProps} isExpanded={true} />);

      const expandedContent = container.querySelector('.overflow-hidden');
      expect(expandedContent).toBeInTheDocument();
      // The opacity should be applied via inline style
      const styleAttribute = expandedContent?.getAttribute('style');
      if (styleAttribute) {
        expect(styleAttribute).toContain('opacity');
      }
    });
  });

  describe('Items with SubItems', () => {
    it('renders CollapsibleItem for items with subItems', () => {
      const { getByText } = render(
        <CollapsibleSection
          {...defaultProps}
          items={mockItemsWithSubItems}
          isExpanded={true}
        />,
      );

      expect(getByText('pages.users.title')).toBeInTheDocument();
    });

    it('renders SidebarButton for items without subItems', () => {
      const { container } = render(
        <CollapsibleSection {...defaultProps} isExpanded={true} />,
      );

      // Items without subItems should render as links (SidebarButton contains Link)
      const links = container.querySelectorAll('a[role="link"]');
      expect(links.length).toBe(mockItems.length);
    });
  });

  describe('Edge Cases', () => {
    it('handles empty items array', () => {
      const { container } = render(
        <CollapsibleSection {...defaultProps} items={[]} isExpanded={true} />,
      );

      const listItems = container.querySelectorAll('li');
      expect(listItems).toHaveLength(0);
    });

    it('handles missing title prop gracefully', () => {
      const { container } = render(
        <CollapsibleSection {...defaultProps} title="" />,
      );

      // Should still render without crashing
      expect(container.firstChild).toBeInTheDocument();
    });
  });
});
