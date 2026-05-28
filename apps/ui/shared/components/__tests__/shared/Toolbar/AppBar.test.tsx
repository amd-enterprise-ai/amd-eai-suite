// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';

import { useRouter } from 'next/router';

import type { SidebarItem } from '@amdenterpriseai/types';

import { AppBar } from '@amdenterpriseai/components';

import { Mock } from 'vitest';

vi.mock('next/router', () => ({
  useRouter: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  usePathname: () => '/test-path',
}));

vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'en' },
  }),
}));

vi.mock('@/src/Navigation/MobileMenu', () => ({
  MobileMenu: () => <div>MobileMenu</div>,
}));

vi.mock('@/src/Navigation/UserMenu', () => ({
  UserMenu: () => <div>UserMenu</div>,
}));

vi.mock('@amdenterpriseai/utils/app', () => ({
  getDocumentationLink: () => '/docs',
  toCamelCase: (str: string) => str,
}));

const emptyMenuItems: SidebarItem[] = [];

describe('AppBar', () => {
  const useRouterMock = useRouter as Mock;

  beforeEach(() => {
    useRouterMock.mockReturnValue({
      pathname: '/test-path',
      locale: 'en',
      defaultLocale: 'en',
    });
  });

  it('renders the AppBar with breadcrumbs', () => {
    const pageBreadcrumb = [
      { href: '/home', title: 'Home' },
      { href: '/test-path', title: 'Test Path' },
    ];

    render(
      <AppBar pageBreadcrumb={pageBreadcrumb} menuItems={emptyMenuItems} />,
    );

    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Test Path')).toBeInTheDocument();
  });

  it('renders the AppBar with title when no breadcrumbs are provided', () => {
    render(<AppBar menuItems={emptyMenuItems} />);

    expect(screen.getByText('pages.test-path.title')).toBeInTheDocument();
  });

  describe('locale-aware breadcrumb hrefs', () => {
    it('does not add locale prefix when locale matches defaultLocale', () => {
      useRouterMock.mockReturnValue({
        pathname: '/test-path',
        locale: 'en',
        defaultLocale: 'en',
      });
      const pageBreadcrumb = [{ href: '/myproject/models', title: 'Models' }];

      render(<AppBar pageBreadcrumb={pageBreadcrumb} />);

      const link = screen.getByRole('link', { name: 'Models' });
      expect(link).toHaveAttribute('href', '/myproject/models');
    });

    it('adds locale prefix when locale differs from defaultLocale', () => {
      useRouterMock.mockReturnValue({
        pathname: '/test-path',
        locale: 'de',
        defaultLocale: 'en',
      });
      const pageBreadcrumb = [{ href: '/myproject/models', title: 'Models' }];

      render(<AppBar pageBreadcrumb={pageBreadcrumb} />);

      const link = screen.getByRole('link', { name: 'Models' });
      expect(link).toHaveAttribute('href', '/de/myproject/models');
    });

    it('handles breadcrumbs without href (no link rendered)', () => {
      useRouterMock.mockReturnValue({
        pathname: '/test-path',
        locale: 'de',
        defaultLocale: 'en',
      });
      const pageBreadcrumb = [{ title: 'Current Page' }];

      render(<AppBar pageBreadcrumb={pageBreadcrumb} />);

      expect(screen.getByText('Current Page')).toBeInTheDocument();
    });
  });
});
