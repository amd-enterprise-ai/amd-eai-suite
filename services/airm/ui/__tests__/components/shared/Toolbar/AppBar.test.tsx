// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';

import { useRouter } from 'next/router';

import { AppBar } from '@/components/shared/Toolbar/AppToolbar';

import { Mock } from 'vitest';

vi.mock('next/router', () => ({
  useRouter: vi.fn(),
}));

vi.mock('@/components/shared//Navigation/MobileMenu', () => {
  const MobileMenu = () => <div>MobileMenu</div>;
  MobileMenu.displayName = 'MobileMenu';
  return { MobileMenu: MobileMenu };
});

vi.mock('@/components/shared/Navigation/UserMenu', () => ({
  UserMenu: () => <div>UserMenu</div>,
}));

describe('AppBar', () => {
  const useRouterMock = useRouter as Mock;

  beforeEach(() => {
    useRouterMock.mockReturnValue({
      pathname: '/test-path',
    });
  });

  it('renders the AppBar with breadcrumbs', () => {
    const pageBreadcrumb = [
      { href: '/home', title: 'Home' },
      { href: '/test-path', title: 'Test Path' },
    ];

    render(<AppBar pageBreadcrumb={pageBreadcrumb} />);

    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Test Path')).toBeInTheDocument();
  });

  it('renders the AppBar with title when no breadcrumbs are provided', () => {
    render(<AppBar />);

    expect(screen.getByText('pages.testPath.title')).toBeInTheDocument();
  });
});
