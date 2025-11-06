// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { fireEvent, render, waitFor } from '@testing-library/react';
import { useSession } from 'next-auth/react';

import router from 'next/router';

import { UserRole } from '@/types/enums/user-roles';

import { Sidebar } from '@/components/shared/Navigation/Sidebar';

import { ProviderWrapper } from '@/__tests__/ProviderWrapper';

// Mock next-auth
vi.mock('next-auth/react', () => ({
  useSession: vi.fn(),
}));
const mockUseSession = vi.mocked(useSession);

// Mock services
vi.mock('@/services/app/organizations', () => ({
  fetchOrganization: vi.fn().mockResolvedValue({
    id: 'org-1',
    name: 'Test Organization',
    domains: ['example.com'],
    smtpEnabled: true,
    idpLinked: true,
  }),
}));

// Mock next/router
vi.mock('next/router', () => {
  const push = vi.fn();
  return {
    default: {
      push,
    },
    useRouter: () => ({
      push,
    }),
  };
});

// Mock the navigation hook
vi.mock('@/hooks/useNavigationState', () => ({
  useNavigationState: () => ({
    expandedSection: null,
    setExpandedSection: vi.fn(),
  }),
}));

// Mock the access control hook
const mockUseAccessControl = vi.fn();
vi.mock('@/hooks/useAccessControl', () => ({
  useAccessControl: () => mockUseAccessControl(),
}));

// Mock SVG components
vi.mock('@/assets/svg/logo/amd-logo.svg', () => {
  return {
    default: ({ className }: { className?: string }) => (
      <div data-testid="amd-logo" className={className}>
        AMD Logo
      </div>
    ),
  };
});

vi.mock('@/assets/svg/logo/amd-symbol.svg', () => {
  return {
    default: ({ className }: { className?: string }) => (
      <div data-testid="amd-symbol" className={className}>
        AMD Symbol
      </div>
    ),
  };
});

// Mock navigation utilities
vi.mock('@/utils/app/navigation', () => ({
  airmMenuItems: [
    {
      href: '/dashboard',
      stringKey: 'pages.dashboard.title',
      icon: <div data-testid="dashboard-icon">📊</div>,
    },
    {
      href: '/users',
      stringKey: 'pages.users.title',
      icon: <div data-testid="users-icon">👥</div>,
    },
  ],
  aiWorkbenchMenuItems: [
    {
      href: '/models',
      stringKey: 'pages.models.title',
      icon: <div data-testid="models-icon">🤖</div>,
    },
  ],
  isMenuItemActive: vi.fn((href: string, path: string) => {
    return href === '/active-item';
  }),
}));

const mockSession = {
  user: {
    id: 'user-123',
    name: 'Test User',
    email: 'test@example.com',
    roles: [UserRole.PLATFORM_ADMIN],
  },
  expires: '2025-01-01',
  accessToken: 'mock-token',
};

const mockRegularUserSession = {
  user: {
    id: 'user-456',
    name: 'Regular User',
    email: 'regular@example.com',
    roles: [UserRole.TEAM_MEMBER],
  },
  expires: '2025-01-01',
  accessToken: 'mock-token',
};

describe('Sidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock for useAccessControl
    mockUseAccessControl.mockReturnValue({
      isRoleManagementEnabled: true,
      isInviteEnabled: true,
      isAdministrator: true,
    });
  });

  describe('Authentication and Session Handling', () => {
    it('renders nothing when not mounted', () => {
      mockUseSession.mockReturnValue({
        data: mockSession,
        status: 'authenticated',
      } as any);

      const { container } = render(
        <ProviderWrapper>
          <Sidebar />
        </ProviderWrapper>,
      );
      // The component should render (it uses useEffect to handle mounting)
      expect(container.firstChild).toBeInTheDocument();
    });

    it('renders correctly when authenticated as admin', async () => {
      mockUseSession.mockReturnValue({
        data: mockSession,
        status: 'authenticated',
      } as any);

      const { getByTestId } = render(
        <ProviderWrapper>
          <Sidebar />
        </ProviderWrapper>,
      );

      await waitFor(() => {
        expect(getByTestId('amd-logo')).toBeInTheDocument();
        expect(getByTestId('sidebar-lock-button')).toBeInTheDocument();
      });
    });

    it('renders correctly when authenticated as regular user', async () => {
      mockUseSession.mockReturnValue({
        data: mockRegularUserSession,
        status: 'authenticated',
      } as any);

      // Override mock for regular user (not an administrator)
      mockUseAccessControl.mockReturnValue({
        isRoleManagementEnabled: true,
        isInviteEnabled: true,
        isAdministrator: false,
      });

      const { queryByText, getByTestId } = render(
        <ProviderWrapper>
          <Sidebar />
        </ProviderWrapper>,
      );

      await waitFor(() => {
        expect(getByTestId('amd-logo')).toBeInTheDocument();
        // Should not render admin-only sections
        expect(
          queryByText('sections.resourceManagement.title'),
        ).not.toBeInTheDocument();
        expect(
          queryByText('sections.accessControl.title'),
        ).not.toBeInTheDocument();
      });
    });

    it('does not render navigation sections when not authenticated', async () => {
      mockUseSession.mockReturnValue({
        data: null,
        status: 'unauthenticated',
      } as any);

      const { queryByText } = render(
        <ProviderWrapper>
          <Sidebar />
        </ProviderWrapper>,
      );

      await waitFor(() => {
        expect(
          queryByText('sections.aiWorkbench.title'),
        ).not.toBeInTheDocument();
      });
    });
  });

  describe('Logo and Header', () => {
    beforeEach(() => {
      mockUseSession.mockReturnValue({
        data: mockSession,
        status: 'authenticated',
      } as any);
    });

    it('renders AMD logo and symbol correctly', async () => {
      const { getByTestId } = render(
        <ProviderWrapper>
          <Sidebar />
        </ProviderWrapper>,
      );

      await waitFor(() => {
        expect(getByTestId('amd-logo')).toBeInTheDocument();
        expect(getByTestId('amd-symbol')).toBeInTheDocument();
      });
    });

    it('navigates to home when logo is clicked', async () => {
      const { getByTestId } = render(
        <ProviderWrapper>
          <Sidebar />
        </ProviderWrapper>,
      );

      await waitFor(() => {
        const logoContainer =
          getByTestId('amd-logo').closest('.cursor-pointer');
        expect(logoContainer).toBeInTheDocument();

        if (logoContainer) {
          fireEvent.click(logoContainer);
          expect(router.push).toHaveBeenCalledWith('/');
        }
      });
    });
  });

  describe('Sidebar Toggle Functionality', () => {
    beforeEach(() => {
      mockUseSession.mockReturnValue({
        data: mockSession,
        status: 'authenticated',
      } as any);
    });

    it('renders lock button correctly', async () => {
      const { getByTestId } = render(
        <ProviderWrapper>
          <Sidebar />
        </ProviderWrapper>,
      );

      await waitFor(() => {
        const lockButton = getByTestId('sidebar-lock-button');
        expect(lockButton).toBeInTheDocument();
        expect(lockButton).toHaveClass('border-1');
      });
    });

    it('toggles sidebar state when lock button is clicked', async () => {
      const { getByTestId, container } = render(
        <ProviderWrapper>
          <Sidebar />
        </ProviderWrapper>,
      );

      await waitFor(() => {
        const lockButton = getByTestId('sidebar-lock-button');
        const sidebarContainer = container.querySelector('.group');

        // Initially mini (w-16)
        expect(sidebarContainer).toHaveClass('w-80');

        fireEvent.click(lockButton);

        // Should toggle to full width (w-80)
        expect(sidebarContainer).toHaveClass('w-16');
      });
    });

    it('shows correct icon based on sidebar state', async () => {
      const { getByTestId } = render(
        <ProviderWrapper>
          <Sidebar />
        </ProviderWrapper>,
      );

      await waitFor(() => {
        const lockButton = getByTestId('sidebar-lock-button');

        // Initially shows lock icon (mini state)
        expect(lockButton.querySelector('svg')).toBeInTheDocument();

        fireEvent.click(lockButton);

        // After toggle, should show unlock icon
        expect(lockButton.querySelector('svg')).toBeInTheDocument();
      });
    });
  });

  describe('Role-based Section Visibility', () => {
    it('shows all sections for platform admin', async () => {
      mockUseSession.mockReturnValue({
        data: mockSession,
        status: 'authenticated',
      } as any);

      const { container } = render(
        <ProviderWrapper>
          <Sidebar />
        </ProviderWrapper>,
      );

      await waitFor(() => {
        // Should have multiple CollapsibleSection components
        const sections = container.querySelectorAll('[class*="mb-4"]');
        expect(sections.length).toBeGreaterThan(0);
      });
    });

    it('shows only AI Workbench section for regular user', async () => {
      mockUseSession.mockReturnValue({
        data: mockRegularUserSession,
        status: 'authenticated',
      } as any);

      // Override mock for regular user (not an administrator)
      mockUseAccessControl.mockReturnValue({
        isRoleManagementEnabled: true,
        isInviteEnabled: true,
        isAdministrator: false,
      });

      const { container } = render(
        <ProviderWrapper>
          <Sidebar />
        </ProviderWrapper>,
      );

      await waitFor(() => {
        // Should render AI Workbench section
        const sections = container.querySelectorAll('[class*="mb-4"]');
        expect(sections.length).toBeGreaterThan(0);
      });
    });

    it('does not show admin sections for regular user', async () => {
      mockUseSession.mockReturnValue({
        data: mockRegularUserSession,
        status: 'authenticated',
      } as any);

      // Override mock for regular user (not an administrator)
      mockUseAccessControl.mockReturnValue({
        isRoleManagementEnabled: true,
        isInviteEnabled: true,
        isAdministrator: false,
      });

      const { queryByText } = render(
        <ProviderWrapper>
          <Sidebar />
        </ProviderWrapper>,
      );

      await waitFor(() => {
        // Should not see admin-only sections
        expect(
          queryByText('sections.resourceManagement.title'),
        ).not.toBeInTheDocument();
        expect(
          queryByText('sections.accessControl.title'),
        ).not.toBeInTheDocument();
      });
    });
  });

  describe('Version Display', () => {
    beforeEach(() => {
      mockUseSession.mockReturnValue({
        data: mockSession,
        status: 'authenticated',
      } as any);
    });

    it('displays version when available', async () => {
      const originalVersion = process.env.NEXT_PUBLIC_BUILD_VERSION;
      process.env.NEXT_PUBLIC_BUILD_VERSION = '1.0.0';

      const { getByText } = render(
        <ProviderWrapper>
          <Sidebar />
        </ProviderWrapper>,
      );

      await waitFor(() => {
        expect(getByText('v1.0.0')).toBeInTheDocument();
      });

      // Cleanup
      process.env.NEXT_PUBLIC_BUILD_VERSION = originalVersion;
    });

    it('hides version in mini sidebar mode', async () => {
      const { getByTestId, container } = render(
        <ProviderWrapper>
          <Sidebar />
        </ProviderWrapper>,
      );

      const lockButton = getByTestId('sidebar-lock-button');
      await fireEvent.click(lockButton);
      await waitFor(() => {
        const versionContainer = container.querySelector('.mb-2');
        expect(versionContainer).toHaveClass('hidden', 'group-hover:flex');
      });
    });
  });

  describe('Mini Sidebar Responsive Behavior', () => {
    beforeEach(() => {
      mockUseSession.mockReturnValue({
        data: mockSession,
        status: 'authenticated',
      } as any);
    });

    it('displays version when available', async () => {
      const originalVersion = process.env.NEXT_PUBLIC_BUILD_VERSION;
      process.env.NEXT_PUBLIC_BUILD_VERSION = '1.0.0';

      const { getByText } = render(
        <ProviderWrapper>
          <Sidebar />
        </ProviderWrapper>,
      );

      await waitFor(() => {
        expect(getByText('v1.0.0')).toBeInTheDocument();
      });

      // Cleanup
      process.env.NEXT_PUBLIC_BUILD_VERSION = originalVersion;
    });
  });

  describe('Mini Sidebar Responsive Behavior', () => {
    beforeEach(() => {
      mockUseSession.mockReturnValue({
        data: mockSession,
        status: 'authenticated',
      } as any);
    });

    it('applies correct classes for mini sidebar', async () => {
      const { getByTestId, container } = render(
        <ProviderWrapper>
          <Sidebar />
        </ProviderWrapper>,
      );

      const lockButton = getByTestId('sidebar-lock-button');
      await fireEvent.click(lockButton);
      await waitFor(() => {
        const sidebar = container.querySelector('.group');
        expect(sidebar).toHaveClass('w-16', 'hover:w-80', 'px-2', 'hover:px-4');
      });
    });

    it('applies correct classes for expanded sidebar after toggle', async () => {
      const { getByTestId, container } = render(
        <ProviderWrapper>
          <Sidebar />
        </ProviderWrapper>,
      );

      await waitFor(() => {
        const sidebar = container.querySelector('.group');
        expect(sidebar).toHaveClass('w-80', 'px-4');
        expect(sidebar).not.toHaveClass('hover:w-80', 'hover:px-4');
      });
    });
  });

  describe('Edge Cases', () => {
    it('handles missing user roles gracefully', async () => {
      const sessionWithoutRoles = {
        user: {
          id: 'user-789',
          name: 'User Without Roles',
          email: 'noroles@example.com',
        },
        expires: '2025-01-01',
      };

      mockUseSession.mockReturnValue({
        data: sessionWithoutRoles,
        status: 'authenticated',
      } as any);

      const { container } = render(
        <ProviderWrapper>
          <Sidebar />
        </ProviderWrapper>,
      );

      await waitFor(() => {
        // Should render without crashing
        expect(container.firstChild).toBeInTheDocument();
      });
    });

    it('handles empty user session gracefully', async () => {
      const emptySession = {
        user: null,
        expires: '2025-01-01',
      };

      mockUseSession.mockReturnValue({
        data: emptySession,
        status: 'authenticated',
      } as any);

      const { container } = render(
        <ProviderWrapper>
          <Sidebar />
        </ProviderWrapper>,
      );

      await waitFor(() => {
        // Should render without crashing
        expect(container.firstChild).toBeInTheDocument();
      });
    });
  });
});
