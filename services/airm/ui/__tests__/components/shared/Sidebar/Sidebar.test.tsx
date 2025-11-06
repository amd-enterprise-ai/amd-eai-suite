// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { render, waitFor } from '@testing-library/react';
import { useSession } from 'next-auth/react';

import { UserRole } from '@/types/enums/user-roles';

import { Sidebar } from '@/components/shared/Navigation/Sidebar';

import { ProviderWrapper } from '@/__tests__/ProviderWrapper';

// Mock next-auth
vi.mock('next-auth/react', () => ({
  useSession: vi.fn(),
}));
const mockUseSession = vi.mocked(useSession);

// Mock Next.js router with factory functions
vi.mock('next/router', () => {
  const mockPush = vi.fn();
  const mockRouter = {
    pathname: '/',
    push: mockPush,
    query: {},
    asPath: '/',
    route: '/',
    basePath: '',
    isLocaleDomain: true,
    isReady: true,
    isPreview: false,
    back: vi.fn(),
    beforePopState: vi.fn(),
    prefetch: vi.fn(),
    reload: vi.fn(),
    replace: vi.fn(),
    events: {
      on: vi.fn(),
      off: vi.fn(),
      emit: vi.fn(),
    },
    isFallback: false,
    locale: undefined,
    locales: undefined,
    defaultLocale: undefined,
  };

  return {
    __esModule: true,
    default: mockRouter,
    useRouter: () => mockRouter,
  };
});

// Mock the menu items
vi.mock('@/utils/app/navigation', () => ({
  airmMenuItems: [
    {
      href: '/',
      name: 'Dashboard',
      stringKey: 'pages.dashboard.title',
      icon: null,
    },
    {
      href: '/projects',
      name: 'Projects',
      stringKey: 'pages.projects.title',
      icon: null,
    },
    {
      href: '/clusters',
      name: 'Clusters',
      stringKey: 'pages.clusters.title',
      icon: null,
    },
    {
      href: '/users',
      name: 'Users',
      stringKey: 'pages.users.title',
      icon: null,
    },
  ],
  aiWorkbenchMenuItems: [
    { href: '/chat', name: 'Chat', stringKey: 'pages.chat.title', icon: null },
    {
      href: '/datasets',
      name: 'Datasets',
      stringKey: 'pages.datasets.title',
      icon: null,
    },
  ],
  isMenuItemActive: (href: string, path: string | null) => {
    if (!path) return false;
    if (href === '/') {
      return path === '/';
    }
    return path === href || path.startsWith(href + '/');
  },
}));

vi.mock('@/assets/svg/logo/amd-logo.svg', () => ({
  default: () => <svg data-testid="amd-logo" />,
}));

vi.mock('@/assets/svg/logo/amd-symbol.svg', () => ({
  default: () => <svg data-testid="amd-symbol" />,
}));

const mockTeamMemberSession = {
  error: null as any,
  expires: '2125-01-01T00:00:00',
  user: {
    id: 'test',
    email: 'testing@test.com',
    roles: [UserRole.TEAM_MEMBER],
  },
};

const mockAdministratorSession = {
  error: null as any,
  expires: '2125-01-01T00:00:00',
  user: {
    id: 'test',
    email: 'testing@test.com',
    roles: [UserRole.PLATFORM_ADMIN],
  },
};

describe('Sidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });
  it('renders sidebar items correctly', () => {
    mockUseSession.mockReturnValue({
      data: mockTeamMemberSession,
      status: 'authenticated',
    } as any);

    const { getByText } = render(
      <ProviderWrapper>
        <Sidebar />
      </ProviderWrapper>,
    );

    expect(getByText('pages.chat.title')).toBeInTheDocument();
  });

  it('renders the sidebar in full mode by default', () => {
    mockUseSession.mockReturnValue({
      data: mockAdministratorSession,
      status: 'authenticated',
    } as any);

    const { container } = render(
      <ProviderWrapper>
        <Sidebar />
      </ProviderWrapper>,
    );

    const sidebar = container.querySelector('div.w-80');
    expect(sidebar).toBeInTheDocument();
  });

  it('toggles sidebar mode when the lock button is clicked', async () => {
    mockUseSession.mockReturnValue({
      data: mockAdministratorSession,
      status: 'authenticated',
    } as any);

    const { getByTestId, container } = render(
      <ProviderWrapper>
        <Sidebar />
      </ProviderWrapper>,
    );

    const lockButton = getByTestId('sidebar-lock-button');
    expect(lockButton).toBeInTheDocument();

    lockButton.click();

    await waitFor(() => {
      container.querySelector('div.w-16');
    });
  });

  it('renders administrator menu items when user has admin role', () => {
    mockUseSession.mockReturnValue({
      data: mockAdministratorSession,
      status: 'authenticated',
    } as any);

    const { getByText } = render(
      <ProviderWrapper>
        <Sidebar />
      </ProviderWrapper>,
    );

    expect(getByText('sections.resourceManagement.title')).toBeVisible();
  });

  it('does not render administrator menu items for non-admin users', () => {
    mockUseSession.mockReturnValue({
      data: mockTeamMemberSession,
      status: 'authenticated',
    } as any);

    const { queryByText } = render(
      <ProviderWrapper>
        <Sidebar />
      </ProviderWrapper>,
    );

    expect(
      queryByText('sections.resourceManagement.title'),
    ).not.toBeInTheDocument();
  });
});
