// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render } from '@testing-library/react';
import { useSession } from 'next-auth/react';

import { SidebarItem, UserRole } from '@amdenterpriseai/types';

import { MobileMenu } from '@amdenterpriseai/components';

import '@testing-library/jest-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const pushMock = vi.fn();

vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock('next/navigation', () => ({
  usePathname: vi.fn(() => '/dashboard'),
}));

vi.mock('next/router', () => ({
  default: { push: (...args: unknown[]) => pushMock(...args) },
  useRouter: () => ({
    push: pushMock,
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
    isMenuItemActive: vi.fn((href: string) => href === '/dashboard'),
  };
});

const mockItems: SidebarItem[] = [
  {
    href: '/dashboard',
    stringKey: 'pages.dashboard.title',
    icon: <div>📊</div>,
  },
  {
    href: '/projects',
    stringKey: 'pages.projects.title',
    icon: <div>📋</div>,
  },
];

const mockItemsWithSubItems: SidebarItem[] = [
  {
    href: '/users',
    stringKey: 'pages.users.title',
    icon: <div>👥</div>,
    subItems: [
      {
        href: '/users/active',
        stringKey: 'pages.users.active',
      },
    ],
  },
];

const baseProps = {
  menuItems: mockItems,
};

const openMenu = (container: HTMLElement) => {
  const toggle = container.querySelector('button');
  if (toggle) {
    fireEvent.click(toggle);
  }
};

describe('MobileMenu', () => {
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

  it('renders only the hamburger toggle while closed', () => {
    const { getByLabelText, queryByText } = render(
      <MobileMenu {...baseProps} />,
    );

    expect(getByLabelText('menu.actions.open')).toBeInTheDocument();
    expect(queryByText('pages.dashboard.title')).not.toBeInTheDocument();
    expect(queryByText('pages.projects.title')).not.toBeInTheDocument();
  });

  it('opens the menu and reveals navigation items when the hamburger is clicked', () => {
    const { container, getByText, getByLabelText } = render(
      <MobileMenu {...baseProps} />,
    );

    openMenu(container);

    expect(getByText('pages.dashboard.title')).toBeInTheDocument();
    expect(getByText('pages.projects.title')).toBeInTheDocument();
    expect(getByLabelText('menu.actions.close')).toBeInTheDocument();
  });

  it('closes the menu when the hamburger is clicked again', () => {
    const { container, queryByText } = render(<MobileMenu {...baseProps} />);

    openMenu(container);
    expect(queryByText('pages.dashboard.title')).toBeInTheDocument();

    openMenu(container);
    expect(queryByText('pages.dashboard.title')).not.toBeInTheDocument();
  });

  it('navigates and closes the menu when an item is selected', () => {
    const { container, getByText, queryByText } = render(
      <MobileMenu {...baseProps} />,
    );

    openMenu(container);
    fireEvent.click(getByText('pages.projects.title'));

    expect(pushMock).toHaveBeenCalledWith('/projects');
    expect(queryByText('pages.projects.title')).not.toBeInTheDocument();
  });

  it('prefixes navigation hrefs with the project prefix', () => {
    const { container, getByText } = render(
      <MobileMenu {...baseProps} projectPrefix="my-project" />,
    );

    openMenu(container);
    fireEvent.click(getByText('pages.projects.title'));

    expect(pushMock).toHaveBeenCalledWith('/my-project/projects');
  });

  it('marks the active item', () => {
    const { container, getByText } = render(<MobileMenu {...baseProps} />);

    openMenu(container);
    const activeItem = getByText('pages.dashboard.title');

    expect(activeItem).toHaveAttribute('aria-current', 'page');
    expect(activeItem).toHaveClass('font-bold');
  });

  it('renders nested sub-items beneath their parent', () => {
    const { container, getByText } = render(
      <MobileMenu menuItems={mockItemsWithSubItems} />,
    );

    openMenu(container);

    expect(getByText('pages.users.title')).toBeInTheDocument();
    expect(getByText('pages.users.active')).toBeInTheDocument();
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

    const { container, queryByText } = render(
      <MobileMenu menuItems={adminOnly} />,
    );

    openMenu(container);

    expect(queryByText('pages.admin.title')).not.toBeInTheDocument();
  });
});
