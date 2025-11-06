// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ActiveUsersTab } from '@/components/features/users/ActiveUsersTab';
import { mockUsersResponse } from '@/__mocks__/services/app/users.data';
import wrapper from '@/__tests__/ProviderWrapper';
import '@testing-library/jest-dom';
import { UserRole } from '@/types/enums/user-roles';
import { useAccessControl } from '@/hooks/useAccessControl';

// Mock next-auth
vi.mock('next-auth/react', () => ({
  useSession: () => ({
    data: {
      accessToken: 'mock-token',
      user: {
        roles: UserRole.PLATFORM_ADMIN,
      },
    },
    status: 'authenticated',
  }),
}));

// Mock useAccessControl
vi.mock('@/hooks/useAccessControl', () => ({
  useAccessControl: vi.fn(),
}));

// Mock useQuery to return our mock data
vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = (await importOriginal()) as any;
  return {
    ...actual,
    useQuery: vi.fn(() => ({
      data: mockUsersResponse,
      isFetching: false,
      isRefetching: false,
      refetch: vi.fn(),
      dataUpdatedAt: new Date(),
    })),
  };
});

// Mock next/router
const mockPush = vi.fn();
vi.mock('next/router', () => ({
  useRouter: () => ({
    push: mockPush,
    pathname: '/users',
    route: '/users',
    query: {},
  }),
}));

const mockUseAccessControl = vi.mocked(useAccessControl);

describe('ActiveUsersTab', () => {
  const mockOnInviteUserClick = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockPush.mockClear();
    // Default mock setup
    mockUseAccessControl.mockReturnValue({
      isRoleManagementEnabled: true,
      isInviteEnabled: true,
      isAdministrator: true,
    });
  });

  it('should render users list', () => {
    render(
      <ActiveUsersTab
        initialData={mockUsersResponse}
        onInviteUserClick={mockOnInviteUserClick}
      />,
      { wrapper },
    );

    mockUsersResponse.users.forEach((user) => {
      expect(
        screen.getByText(`${user.firstName} ${user.lastName}`),
      ).toBeInTheDocument();
      expect(screen.getByText(user.email)).toBeInTheDocument();
    });
  });

  it('should call onInviteUserClick when invite button is clicked', async () => {
    render(
      <ActiveUsersTab
        initialData={mockUsersResponse}
        onInviteUserClick={mockOnInviteUserClick}
      />,
      { wrapper },
    );

    const inviteButton = screen.getByLabelText('actions.addUser');
    fireEvent.click(inviteButton);

    expect(mockOnInviteUserClick).toHaveBeenCalledTimes(1);
  });

  it('should handle row click and navigate to user details', async () => {
    render(
      <ActiveUsersTab
        initialData={mockUsersResponse}
        onInviteUserClick={mockOnInviteUserClick}
      />,
      { wrapper },
    );

    const row = screen.getByText('FirstName 2 LastName 2').closest('tr');
    expect(row).toBeInTheDocument();

    if (row) {
      fireEvent.click(row);
    }

    expect(mockPush).toHaveBeenCalledWith('/users/2');
  });

  it('should handle filter changes internally', async () => {
    render(
      <ActiveUsersTab
        initialData={mockUsersResponse}
        onInviteUserClick={mockOnInviteUserClick}
      />,
      { wrapper },
    );

    const filterInput = screen.getByPlaceholderText('list.filter.placeholder');

    // The component should handle its own filter logic now
    fireEvent.change(filterInput, { target: { value: 'test' } });

    // Verify the input value is updated (internal state management)
    await waitFor(() => {
      expect(filterInput).toHaveValue('test');
    });
  });

  // SDA-2328: Tests for Last Seen At column replacement
  describe('SDA-2328: Last Seen At column', () => {
    it('should display Last Seen At column header', () => {
      render(
        <ActiveUsersTab
          initialData={mockUsersResponse}
          onInviteUserClick={mockOnInviteUserClick}
        />,
        { wrapper },
      );

      // Verify Last Seen At header is present
      expect(
        screen.getByText('list.headers.lastSeenAt.title'),
      ).toBeInTheDocument();
    });

    it('should display formatted date and time for users with lastActiveAt', () => {
      render(
        <ActiveUsersTab
          initialData={mockUsersResponse}
          onInviteUserClick={mockOnInviteUserClick}
        />,
        { wrapper },
      );

      // Mock users (except first) have lastActiveAt dates
      // We should see formatted date and time in YYYY/MM/DD HH:MM format
      const dateTimeElements = screen.getAllByText(
        /\d{4}\/\d{2}\/\d{2} \d{2}:\d{2}/,
      );
      expect(dateTimeElements.length).toBeGreaterThan(0);
    });

    it('should display Never for users without lastActiveAt', () => {
      render(
        <ActiveUsersTab
          initialData={mockUsersResponse}
          onInviteUserClick={mockOnInviteUserClick}
        />,
        { wrapper },
      );

      // First user has no lastActiveAt, should show "Never"
      expect(screen.getByText('list.lastSeenAt.never')).toBeInTheDocument();
    });

    it('should have correct column order: Name, Email, Last Seen At, Roles', () => {
      render(
        <ActiveUsersTab
          initialData={mockUsersResponse}
          onInviteUserClick={mockOnInviteUserClick}
        />,
        { wrapper },
      );

      // Get all column headers
      const headers = screen.getAllByRole('columnheader');

      // Verify the expected headers are present in order
      expect(headers[0]).toHaveTextContent('list.headers.name.title');
      expect(headers[1]).toHaveTextContent('list.headers.email.title');
      expect(headers[2]).toHaveTextContent('list.headers.lastSeenAt.title');
      expect(headers[3]).toHaveTextContent('list.headers.roles.title');
    });
  });

  // Additional tests for navigation scenarios
  describe('Navigation scenarios with different access control states', () => {
    it('should navigate correctly regardless of invite enabled status', () => {
      // Test that navigation works the same whether invite is enabled or not
      const accessControlStates = [
        { isInviteEnabled: false },
        { isInviteEnabled: true },
      ];

      accessControlStates.forEach((state) => {
        mockUseAccessControl.mockReturnValue({
          isRoleManagementEnabled: true,
          isAdministrator: true,
          ...state,
        });

        const { unmount } = render(
          <ActiveUsersTab
            initialData={mockUsersResponse}
            onInviteUserClick={mockOnInviteUserClick}
          />,
          { wrapper },
        );

        // Navigation should work regardless of access control state
        const userRow = screen
          .getByText('FirstName 1 LastName 1')
          .closest('tr');
        if (userRow) {
          fireEvent.click(userRow);
        }

        expect(mockPush).toHaveBeenCalledWith('/users/1');

        unmount();
        mockPush.mockClear();
      });
    });

    it('should handle navigation for different user IDs correctly', () => {
      render(
        <ActiveUsersTab
          initialData={mockUsersResponse}
          onInviteUserClick={mockOnInviteUserClick}
        />,
        { wrapper },
      );

      // Test multiple users
      const userTests = [
        { name: 'FirstName 2 LastName 2', expectedId: '2' },
        { name: 'FirstName 3 LastName 3', expectedId: '3' },
        { name: 'FirstName 4 LastName 4', expectedId: '4' },
      ];

      userTests.forEach((test) => {
        const userRow = screen.getByText(test.name).closest('tr');
        expect(userRow).toBeInTheDocument();

        if (userRow) {
          fireEvent.click(userRow);
        }

        expect(mockPush).toHaveBeenCalledWith(`/users/${test.expectedId}`);
      });
    });
  });
});
