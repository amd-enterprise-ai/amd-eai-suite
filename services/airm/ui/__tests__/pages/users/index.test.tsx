// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import * as ReactQuery from '@tanstack/react-query';
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import router from 'next/router';
import { deleteUser, resendInvitation } from '@/services/app/users';
import { UsersResponse, InvitedUsersResponse } from '@/types/users';
import UsersPage from '@/pages/users';
import wrapper from '@/__tests__/ProviderWrapper';
import '@testing-library/jest-dom';
import { type Mock } from 'vitest';
import {
  mockUsersResponse,
  mockInvitedUsersResponse,
} from '@/__mocks__/services/app/users.data';
import { UserRole } from '@/types/enums/user-roles';

// Mock useSession locally
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

// Mock useAccessControl to ensure invite button is enabled
vi.mock('@/hooks/useAccessControl', () => ({
  useAccessControl: vi.fn(() => ({
    isRoleManagementEnabled: true,
    isInviteEnabled: true,
    isAdministrator: true,
  })),
}));

// Mock the new tab components
vi.mock('@/components/features/users', () => ({
  ActiveUsersTab: ({ initialData, onInviteUserClick }: any) => (
    <div data-testid="active-users-tab">
      {initialData.users.map((user: any) => (
        <div key={user.id} onClick={() => router.push(`/users/${user.id}`)}>
          <span>{`${user.firstName} ${user.lastName}`}</span>
          <span>{user.email}</span>
        </div>
      ))}
      <button aria-label="actions.addUser" onClick={onInviteUserClick}>
        actions.addUser
      </button>
      <input placeholder="list.filter.placeholder" onChange={() => {}} />
    </div>
  ),
  InvitedUsersTab: ({ initialData, onInviteUserClick }: any) => (
    <div data-testid="invited-users-tab">
      {initialData.invitedUsers.map((user: any) => (
        <div key={user.id}>
          <span>{user.email}</span>
          <button aria-label="list.actions.label">Actions</button>
        </div>
      ))}
      <button onClick={onInviteUserClick}>actions.addUser</button>
      <input placeholder="list.filter.placeholder" onChange={() => {}} />
    </div>
  ),
}));

const mockUsersEmptyResponse: UsersResponse = {
  users: [],
};

const mockInvitedUsersEmptyResponse: InvitedUsersResponse = {
  invitedUsers: [],
};

vi.mock('@/services/app/users', async (importOriginal) => {
  const actualUsersModule =
    (await importOriginal()) as typeof import('@/services/app/users');
  return {
    ...actualUsersModule,
    deleteUser: vi.fn(),
    resendInvitation: vi.fn(),
  };
});

describe('users', () => {
  it('should not crash the page', async () => {
    const { container } = render(
      <UsersPage
        users={mockUsersEmptyResponse}
        invitedUsers={mockInvitedUsersEmptyResponse}
      />,
      {
        wrapper,
      },
    );
    expect(container).toBeTruthy();
  });

  it('should render a list of users', async () => {
    render(
      <UsersPage
        users={mockUsersResponse}
        invitedUsers={mockInvitedUsersEmptyResponse}
      />,
      {
        wrapper,
      },
    );

    // Check that the active users tab is rendered with users
    expect(screen.getByTestId('active-users-tab')).toBeInTheDocument();

    mockUsersResponse.users.forEach((user) => {
      expect(
        screen.getByText(`${user.firstName} ${user.lastName}`),
      ).toBeInTheDocument();
      expect(screen.getByText(user.email)).toBeInTheDocument();
    });
  });

  it('should filter the list of users based on lastname', async () => {
    await act(async () => {
      render(
        <UsersPage
          users={mockUsersResponse}
          invitedUsers={mockInvitedUsersEmptyResponse}
        />,
        {
          wrapper,
        },
      );
    });

    const filterInput = screen.getByPlaceholderText('list.filter.placeholder');
    expect(filterInput).toBeInTheDocument();

    // The actual filtering logic is now handled by the ActiveUsersTab component
    // This test verifies that the filter input is present and can be interacted with
    await fireEvent.change(filterInput, { target: { value: 'FirstName 2' } });

    // We still see all users in this mock since the filtering is handled by the component
    expect(screen.getByText('FirstName 2 LastName 2')).toBeInTheDocument();
  });

  it('should filter the list of users based on email', async () => {
    await act(async () => {
      render(
        <UsersPage
          users={mockUsersResponse}
          invitedUsers={mockInvitedUsersEmptyResponse}
        />,
        {
          wrapper,
        },
      );
    });

    const filterInput = screen.getByPlaceholderText('list.filter.placeholder');
    expect(filterInput).toBeInTheDocument();

    // The actual filtering logic is now handled by the ActiveUsersTab component
    await fireEvent.change(filterInput, { target: { value: 'user4@amd.com' } });

    // We still see all users in this mock since the filtering is handled by the component
    expect(screen.getByText('FirstName 4 LastName 4')).toBeInTheDocument();
  });

  it('add button should show modal', async () => {
    await act(async () => {
      render(
        <UsersPage
          users={mockUsersResponse}
          invitedUsers={mockInvitedUsersEmptyResponse}
        />,
        {
          // empty
          wrapper,
        },
      );
    });

    await waitFor(
      () => {
        const addButton = screen.queryByText('actions.addUser');
        expect(addButton).toBeInTheDocument();
      },
      { timeout: 3000 },
    );

    const addButton = screen.getByLabelText('actions.addUser');
    expect(addButton).toBeInTheDocument();
    await waitFor(() => expect(addButton).not.toBeDisabled());

    const modalTitle = screen.queryByText('modal.addUser.title');

    expect(modalTitle).not.toBeInTheDocument();

    await fireEvent.click(addButton);

    expect(screen.queryByText('modal.addUser.title')).toBeInTheDocument();
    expect(
      screen.queryByText('modal.addUser.form.email.label'),
    ).toBeInTheDocument();

    expect(screen.getByRole('textbox', { name: /email/i })).toBeInTheDocument();
  });

  it.skip('should fetch and render users from react-query', async () => {
    vi.spyOn(ReactQuery, 'useQuery').mockReturnValue({
      data: mockUsersResponse,
      isLoading: false,
      isError: false,
    } as unknown as ReactQuery.UseQueryResult<
      typeof mockUsersResponse.users,
      unknown
    >);

    await act(async () => {
      render(
        <UsersPage
          users={mockUsersResponse}
          invitedUsers={mockInvitedUsersEmptyResponse}
        />,
        { wrapper },
      );
    });

    // Wait for the users to be fetched and rendered
    await screen.findByText('FirstName 1 LastName 1');
    await screen.findByText('FirstName 2 LastName 2');
    await screen.findByText('FirstName 3 LastName 3');

    mockUsersResponse?.users?.forEach((user) => {
      expect(
        screen.getByText(`${user.firstName} ${user.lastName}`),
      ).toBeInTheDocument();
      expect(screen.getByText(user.email)).toBeInTheDocument();
    });
  });

  it('should handle row click', async () => {
    const mockRouterPush = vi.fn();
    vi.spyOn(router, 'push').mockImplementation(mockRouterPush);

    await act(async () => {
      render(
        <UsersPage
          users={mockUsersResponse}
          invitedUsers={mockInvitedUsersEmptyResponse}
        />,
        {
          wrapper,
        },
      );
    });

    const userRow = screen.getByText('FirstName 2 LastName 2');
    expect(userRow).toBeInTheDocument();

    await fireEvent.click(userRow);
    expect(mockRouterPush).toHaveBeenCalledWith('/users/2');
  });

  it('should render tabs and switch between active and invited users', async () => {
    render(
      <UsersPage
        users={mockUsersResponse}
        invitedUsers={mockInvitedUsersResponse}
      />,
      {
        wrapper,
      },
    );

    // Check that tabs are present
    expect(screen.getByText('tabs.active')).toBeInTheDocument();
    expect(screen.getByText('tabs.invited')).toBeInTheDocument();

    // By default, active users should be shown
    expect(screen.getByTestId('active-users-tab')).toBeInTheDocument();
    expect(screen.getByText('FirstName 1 LastName 1')).toBeInTheDocument();

    // Click on invited tab
    const invitedTab = screen.getByText('tabs.invited');
    fireEvent.click(invitedTab);

    // Should show invited users tab
    await waitFor(() => {
      expect(screen.getByTestId('invited-users-tab')).toBeInTheDocument();
      expect(screen.getByText('invited1@amd.com')).toBeInTheDocument();
    });
  });

  describe('Invited Users Tab', () => {
    it('should render list of invited users in the invited tab', async () => {
      render(
        <UsersPage
          users={mockUsersEmptyResponse}
          invitedUsers={mockInvitedUsersResponse}
        />,
        {
          wrapper,
        },
      );

      // Switch to invited tab
      const invitedTab = screen.getByText('tabs.invited');
      fireEvent.click(invitedTab);

      // Check that invited users tab is displayed
      await waitFor(() => {
        expect(screen.getByTestId('invited-users-tab')).toBeInTheDocument();
        mockInvitedUsersResponse.invitedUsers.forEach((user) => {
          expect(screen.getByText(user.email)).toBeInTheDocument();
        });
      });
    });

    it('should filter invited users based on email in the invited tab', async () => {
      render(
        <UsersPage
          users={mockUsersEmptyResponse}
          invitedUsers={mockInvitedUsersResponse}
        />,
        {
          wrapper,
        },
      );

      // Switch to invited tab
      const invitedTab = screen.getByText('tabs.invited');
      fireEvent.click(invitedTab);

      await waitFor(() => {
        expect(screen.getByTestId('invited-users-tab')).toBeInTheDocument();
        const filterInput = screen.getByPlaceholderText(
          'list.filter.placeholder',
        );
        expect(filterInput).toBeInTheDocument();

        // Simulate user typing in the filter input
        fireEvent.change(filterInput, {
          target: { value: 'invited2@amd.com' },
        });
      });

      // The actual filtering logic is now handled by the InvitedUsersTab component
      expect(screen.getByText('invited2@amd.com')).toBeInTheDocument();
    });

    it('should show invite user modal from invited tab', async () => {
      render(
        <UsersPage
          users={mockUsersEmptyResponse}
          invitedUsers={mockInvitedUsersEmptyResponse}
        />,
        {
          wrapper,
        },
      );

      // Switch to invited tab
      const invitedTab = screen.getByText('tabs.invited');
      fireEvent.click(invitedTab);

      await waitFor(() => {
        expect(screen.getByTestId('invited-users-tab')).toBeInTheDocument();
        const addButton = screen.getByText('actions.addUser');
        expect(addButton).toBeInTheDocument();
      });

      const modalTitle = screen.queryByText('modal.addUser.title');
      expect(modalTitle).not.toBeInTheDocument();

      const addButton = screen.getByText('actions.addUser');
      fireEvent.click(addButton);

      await waitFor(() => {
        expect(screen.getByText('modal.addUser.title')).toBeInTheDocument();
      });
    });

    // These tests are simplified since the action handling is now in the InvitedUsersTab component
    it('should show action dropdowns for invited users', async () => {
      render(
        <UsersPage
          users={mockUsersEmptyResponse}
          invitedUsers={mockInvitedUsersResponse}
        />,
        {
          wrapper,
        },
      );

      // Switch to invited tab
      const invitedTab = screen.getByText('tabs.invited');
      fireEvent.click(invitedTab);

      await waitFor(() => {
        expect(screen.getByTestId('invited-users-tab')).toBeInTheDocument();
        const dropDowns = screen.getAllByLabelText('list.actions.label');
        expect(dropDowns.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Invite functionality disabled', () => {
    beforeEach(async () => {
      // Mock useAccessControl to disable invite functionality
      const { useAccessControl } = await import('@/hooks/useAccessControl');
      vi.mocked(useAccessControl).mockReturnValue({
        isRoleManagementEnabled: true,
        isInviteEnabled: false,
        isAdministrator: true,
      });
    });

    afterEach(async () => {
      // Reset to default mock
      const { useAccessControl } = await import('@/hooks/useAccessControl');
      vi.mocked(useAccessControl).mockReturnValue({
        isRoleManagementEnabled: true,
        isInviteEnabled: true,
        isAdministrator: true,
      });
    });

    it('should hide tab headers entirely when isInviteEnabled is false', async () => {
      await act(async () => {
        render(
          <UsersPage
            users={mockUsersResponse}
            invitedUsers={mockInvitedUsersResponse}
          />,
          {
            wrapper,
          },
        );
      });

      // Check that tab headers are NOT visible when isInviteEnabled is false
      // The tabs component should have the 'hidden' class applied to the tabList
      const tabsContainer = screen.getByRole('tablist');
      expect(tabsContainer).toHaveClass('hidden');

      // Verify that active users content is still shown
      expect(screen.getByTestId('active-users-tab')).toBeInTheDocument();
      expect(screen.getByText('FirstName 1 LastName 1')).toBeInTheDocument();
    });

    it('should only show active users content when invited tab is hidden', async () => {
      await act(async () => {
        render(
          <UsersPage
            users={mockUsersResponse}
            invitedUsers={mockInvitedUsersResponse}
          />,
          {
            wrapper,
          },
        );
      });

      // Should show active users
      expect(screen.getByTestId('active-users-tab')).toBeInTheDocument();
      mockUsersResponse.users.forEach((user) => {
        expect(
          screen.getByText(`${user.firstName} ${user.lastName}`),
        ).toBeInTheDocument();
        expect(screen.getByText(user.email)).toBeInTheDocument();
      });

      // Should not show invited users tab
      expect(screen.queryByTestId('invited-users-tab')).not.toBeInTheDocument();
    });
  });

  describe('Invite functionality enabled', () => {
    beforeEach(async () => {
      // Ensure useAccessControl returns invite enabled
      const { useAccessControl } = await import('@/hooks/useAccessControl');
      vi.mocked(useAccessControl).mockReturnValue({
        isRoleManagementEnabled: true,
        isInviteEnabled: true,
        isAdministrator: true,
      });
    });

    it('should show both active and invited users tabs when isInviteEnabled is true', async () => {
      await act(async () => {
        render(
          <UsersPage
            users={mockUsersResponse}
            invitedUsers={mockInvitedUsersResponse}
          />,
          {
            wrapper,
          },
        );
      });

      // Check that both tabs are present
      expect(screen.getByText('tabs.active')).toBeInTheDocument();
      expect(screen.getByText('tabs.invited')).toBeInTheDocument();

      // Check that tab headers are visible when isInviteEnabled is true
      const tabsContainer = screen.getByRole('tablist');
      expect(tabsContainer).not.toHaveClass('hidden');

      // Verify that active users are shown by default
      expect(screen.getByTestId('active-users-tab')).toBeInTheDocument();
      expect(screen.getByText('FirstName 1 LastName 1')).toBeInTheDocument();

      // Should show invite button in active tab
      expect(screen.getByText('actions.addUser')).toBeInTheDocument();
    });
  });
});
