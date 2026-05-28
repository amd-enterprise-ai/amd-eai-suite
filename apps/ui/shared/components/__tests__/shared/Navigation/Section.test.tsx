// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, waitFor } from '@testing-library/react';
import { useSession } from 'next-auth/react';
import { IconServer } from '@tabler/icons-react';

import { SidebarItem, UserRole } from '@amdenterpriseai/types';

import { Section } from '@amdenterpriseai/components';

import '@testing-library/jest-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock('next/navigation', () => ({
  usePathname: vi.fn(() => '/dashboard'),
}));

vi.mock('next/router', () => ({
  useRouter: () => ({
    push: vi.fn(),
    query: {},
    locale: 'en',
    defaultLocale: 'en',
  }),
}));

vi.mock('next-auth/react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('next-auth/react')>();
  return {
    ...actual,
    useSession: vi.fn(() => ({
      data: {
        user: { id: 'u1', email: 'a@b.com', roles: [UserRole.PLATFORM_ADMIN] },
        expires: '2099-01-01',
      },
      status: 'authenticated',
    })),
  };
});

vi.mock('@amdenterpriseai/utils/app', async (importOriginal) => {
  const actual =
    await importOriginal<typeof import('@amdenterpriseai/utils/app')>();
  return {
    ...actual,
    isMenuItemActive: vi.fn((href: string, path: string) => {
      return href === '/active-item';
    }),
  };
});

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

const baseProps = {
  title: 'sections.resourceManagement.title',
  items: mockItems,
  isSidebarMini: false,
};

describe('Section (Section)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useSession).mockReturnValue({
      data: {
        user: { id: 'u1', email: 'a@b.com', roles: [UserRole.PLATFORM_ADMIN] },
        expires: '2099-01-01',
      },
      status: 'authenticated',
    } as ReturnType<typeof useSession>);
  });

  it('renders flat menu items as links with string keys', () => {
    const { getByText, getAllByRole } = render(<Section {...baseProps} />);

    expect(getByText('pages.dashboard.title')).toBeInTheDocument();
    expect(getByText('pages.projects.title')).toBeInTheDocument();
    expect(getAllByRole('link')).toHaveLength(mockItems.length);
  });

  it('renders item icons for flat links', () => {
    const { getByTestId } = render(<Section {...baseProps} />);

    expect(getByTestId('dashboard-icon')).toBeInTheDocument();
    expect(getByTestId('projects-icon')).toBeInTheDocument();
  });

  it('renders CollapsibleItem (expand control) when an item has subItems', () => {
    const { getByText, container } = render(
      <Section {...baseProps} items={mockItemsWithSubItems} />,
    );

    expect(getByText('pages.users.title')).toBeInTheDocument();
    expect(container.querySelector('button')).toBeInTheDocument();
  });

  it('applies animated height on the content wrapper', async () => {
    const { container } = render(<Section {...baseProps} />);

    await waitFor(() => {
      const animated = container.querySelector('.transition-all.duration-200');
      expect(animated).toBeInTheDocument();
      const style = animated?.getAttribute('style') ?? '';
      expect(style).toMatch(/height:\s*\d+px/);
    });
  });

  it('renders no list rows when items is empty', () => {
    const { container } = render(<Section {...baseProps} items={[]} />);

    expect(container.querySelectorAll('li')).toHaveLength(0);
  });

  it('hides items the user role cannot access', () => {
    vi.mocked(useSession).mockReturnValue({
      data: {
        user: { id: 'u2', email: 'm@b.com', roles: [UserRole.TEAM_MEMBER] },
        expires: '2099-01-01',
      },
      status: 'authenticated',
    } as ReturnType<typeof useSession>);

    const adminOnly: SidebarItem[] = [
      {
        href: '/admin',
        stringKey: 'pages.admin.title',
        visibilityByRole: new Set([UserRole.PLATFORM_ADMIN]),
      },
    ];

    const { queryByText } = render(
      <Section {...baseProps} items={adminOnly} />,
    );

    expect(queryByText('pages.admin.title')).not.toBeInTheDocument();
  });
});
