// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';

import {
  addUsersToProject,
  deleteUserFromProject,
} from '@/services/app/projects';
import { fetchInvitedUsers, fetchUsers } from '@/services/app/users';

import { generateMockProjects } from '../../../../__mocks__/utils/project-mock';

import { ProjectWithMembers } from '@/types/projects';

import { Members } from '@/components/features/projects';

import wrapper from '@/__tests__/ProviderWrapper';
import userEvent from '@testing-library/user-event';
import { Mock } from 'vitest';

// Mock next-i18next
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: any) => {
      if (params) {
        // Simple parameter replacement for testing
        let result = key;
        Object.keys(params).forEach((param) => {
          result = result.replace(
            new RegExp(`\\{\\{${param}\\}\\}`, 'g'),
            params[param],
          );
        });
        return result;
      }
      return key;
    },
  }),
  Trans: ({ children }: { children: React.ReactNode }) => children,
}));

const toastSuccessMock = vi.fn();
const toastErrorMock = vi.fn();
vi.mock('@/hooks/useSystemToast', () => {
  const useSystemToast = () => {
    const toast = vi.fn() as any;
    toast.success = toastSuccessMock;
    toast.error = toastErrorMock;
    return { toast };
  };
  return { default: useSystemToast };
});

vi.mock('@/services/app/projects', async (importOriginal) => {
  return {
    ...(await importOriginal()),
    deleteUserFromProject: vi.fn(),
    addUsersToProject: vi.fn(),
  };
});

vi.mock('@/services/app/users', () => ({
  fetchUsers: vi.fn(),
  fetchInvitedUsers: vi.fn(),
}));

vi.mock('@/hooks/useAccessControl', () => ({
  useAccessControl: () => ({
    isRoleManagementEnabled: true,
  }),
}));

// Mock Tabler icons
vi.mock('@tabler/icons-react', async (importOriginal) => {
  const original = (await importOriginal()) ?? {};
  return {
    ...original,
    IconDotsVertical: ({ className }: any) => (
      <span className={className}>action-dot-icon</span>
    ),
  };
});

const mockUpdate = vi.fn();

vi.mock('next-auth/react', () => ({
  useSession: () => ({
    data: {
      user: {
        email: 'test@example.com',
        id: 'test-user-id',
      },
    },
    update: mockUpdate,
  }),
}));

const mockProjectWithMembers: ProjectWithMembers = {
  ...generateMockProjects(1)[0],
  users: [
    {
      id: 'user1',
      firstName: 'Biba',
      lastName: 'Bobin',
      role: 'Team Member',
      email: 'biba.bobin@company.com',
    },
  ],
  invitedUsers: [
    {
      id: 'invUser1',
      role: 'Platform Administrator',
      email: 'invUser1@company.com',
    },
  ],
};

const mockProjectWithMultipleMembers: ProjectWithMembers = {
  ...mockProjectWithMembers,
  users: [
    {
      id: 'user1',
      firstName: 'Biba',
      lastName: 'Bobin',
      role: 'Team Member',
      email: 'biba.bobin@company.com',
    },
    {
      id: 'user2',
      firstName: 'Boba',
      lastName: 'Bibin',
      role: 'Project Manager',
      email: 'boba.bibin@company.com',
    },
    {
      id: 'user3',
      firstName: 'Pupa',
      lastName: 'Lupin',
      role: 'Developer',
      email: 'pupa.lupin@company.com',
    },
    {
      id: 'user4',
      firstName: 'Lupa',
      lastName: 'Pupin',
      role: 'Designer',
      email: 'lupa.pupin@company.com',
    },
  ],
};

const queryClient = new QueryClient();

describe('Members', () => {
  const mockDeleteUserFromProject = deleteUserFromProject as Mock;
  const mockAddUsersToProject = addUsersToProject as Mock;
  const mockFetchUsers = fetchUsers as Mock;
  const mockFetchInvitedUsers = fetchInvitedUsers as Mock;

  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders the component with members', () => {
    act(() => {
      render(<Members project={mockProjectWithMembers} />, { wrapper });
    });
    expect(
      screen.getByText('settings.membersAndInvitedUsers.members.title'),
    ).toBeInTheDocument();
    expect(screen.getByText('Biba Bobin')).toBeInTheDocument();
  });

  it('renders the component without members', () => {
    act(() => {
      render(<Members project={{ ...mockProjectWithMembers, users: [] }} />, {
        wrapper,
      });
    });
    expect(
      screen.getByText('settings.membersAndInvitedUsers.members.title'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('settings.membersAndInvitedUsers.members.empty'),
    ).toBeInTheDocument();
  });

  it('opens the remove confirmation modal when remove button is clicked', async () => {
    const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries');
    mockDeleteUserFromProject.mockImplementation(() => Promise.resolve());

    await act(async () => {
      render(
        <QueryClientProvider client={queryClient}>
          <Members project={mockProjectWithMembers} />
        </QueryClientProvider>,
      );
    });

    const contextMenuButton = screen.getByLabelText('list.actions.label');
    await fireEvent.click(contextMenuButton);

    const deleteButton = screen.getByLabelText(
      'settings.membersAndInvitedUsers.members.actions.remove.label',
    );
    await fireEvent.click(deleteButton);

    const deleteConfirmButton = screen.getByText('actions.confirm.title');
    await fireEvent.click(deleteConfirmButton);

    await waitFor(() => {
      expect(mockDeleteUserFromProject).toHaveBeenCalledWith({
        projectId: '1',
        userId: 'user1',
      });
      expect(invalidateQueriesSpy).toHaveBeenCalledWith({
        queryKey: ['project'],
      });
      expect(toastSuccessMock).toBeCalledWith(
        'settings.membersAndInvitedUsers.members.actions.remove.notification.success',
      );
    });

    invalidateQueriesSpy.mockRestore();
  });

  it('disables add user modal if there are no additional candidates', async () => {
    mockFetchUsers.mockResolvedValue({
      users: [
        {
          id: 'user1',
        },
      ],
    });

    await act(() => {
      render(<Members project={mockProjectWithMembers} />, { wrapper });
    });
    const addButton = screen.getByLabelText(
      'settings.membersAndInvitedUsers.members.actions.add',
    ) as HTMLInputElement;

    expect(addButton.disabled).toBeTruthy();
  });

  it('calls addUsersToProjectAPI with the correct value there are candidates and users are added', async () => {
    mockFetchUsers.mockResolvedValue({
      users: [
        {
          id: 'user1',
          firstName: 'User',
          lastName: 'One',
          email: 'user1@company.com',
        },
        {
          id: 'user2',
          firstName: 'User',
          lastName: 'Two',
          email: 'user2@company.com',
        },
        {
          id: 'user3',
          firstName: 'User',
          lastName: 'Three',
          email: 'user3@company.com',
        },
        {
          id: 'user4',
          firstName: 'User',
          lastName: 'Four',
          email: 'user4@company.com',
        },
      ],
    });

    mockFetchInvitedUsers.mockResolvedValue({
      invitedUsers: [
        {
          id: 'invUser1',
          email: 'invUser1@company.com',
        },
        {
          id: 'invUser2',
          email: 'invUser2@company.com',
        },
        {
          id: 'invUser3',
          email: 'invUser3@company.com',
        },
      ],
    });

    await act(async () => {
      render(<Members project={mockProjectWithMembers} />, { wrapper });
    });
    const addButton = screen.getByLabelText(
      'settings.membersAndInvitedUsers.members.actions.add',
    ) as HTMLInputElement;

    await waitFor(() => expect(addButton.disabled).toBeFalsy());
    fireEvent.click(addButton);

    fireEvent.click(
      screen.getAllByLabelText(
        'settings.membersAndInvitedUsers.members.actions.add.form.users.label',
      )[1],
    );
    fireEvent.click(screen.getByRole('option', { name: 'user2@company.com' }));

    fireEvent.click(
      screen.getAllByLabelText(
        'settings.membersAndInvitedUsers.members.actions.add.form.users.label',
      )[1],
    );
    fireEvent.click(screen.getByRole('option', { name: 'user3@company.com' }));

    fireEvent.click(
      screen.getAllByLabelText(
        'settings.membersAndInvitedUsers.members.actions.add.form.users.label',
      )[1],
    );
    fireEvent.click(
      screen.getByRole('option', { name: 'invUser3@company.com' }),
    );

    const confirmButton = screen.getByText(
      'settings.membersAndInvitedUsers.members.actions.add.modal.confirm',
    );
    fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(mockAddUsersToProject).toHaveBeenCalledWith({
        projectId: '1',
        userIds: ['user2', 'user3', 'invUser3'],
      });
      expect(toastSuccessMock).toBeCalledWith(
        'settings.membersAndInvitedUsers.members.actions.add.notification.success',
      );
    });
  });

  it('renders members sorted by full name (case-insensitive)', async () => {
    const mixedCaseUsers = [
      {
        id: 'userA',
        firstName: 'alice',
        lastName: 'Zephyr',
        role: 'Engineer',
        email: 'alice@company.com',
      },
      {
        id: 'userB',
        firstName: 'Bob',
        lastName: 'Yellow',
        role: 'Engineer',
        email: 'bob@company.com',
      },
      {
        id: 'userC',
        firstName: 'charlie',
        lastName: 'alpha',
        role: 'Engineer',
        email: 'charlie@company.com',
      },
    ];

    const mockSortedProject = {
      ...mockProjectWithMembers,
      users: mixedCaseUsers,
    };

    await act(async () => {
      render(<Members project={mockSortedProject} />, { wrapper });
    });

    const nameColumnHeader = screen.getByText('list.users.headers.name.title');
    fireEvent.click(nameColumnHeader);

    const tableRows = screen.getAllByRole('row').filter((row) => {
      return row.querySelector('td') !== null;
    });

    const nameTexts: string[] = tableRows.map((row) => {
      const cells = row.querySelectorAll('td');
      return cells[0]?.textContent?.trim() ?? '';
    });

    expect(nameTexts).toEqual(['charlie alpha', 'Bob Yellow', 'alice Zephyr']);
  });

  describe('Search Functionality', () => {
    beforeEach(() => {
      vi.clearAllMocks();
    });

    it('renders search input with correct placeholder', () => {
      render(<Members project={mockProjectWithMembers} />, { wrapper });

      const searchInput = screen.getByPlaceholderText(
        'list.filter.search.placeholder',
      );
      expect(searchInput).toBeInTheDocument();
    });

    it('filters users by first name', async () => {
      const user = userEvent.setup();
      render(<Members project={mockProjectWithMultipleMembers} />, { wrapper });

      const searchInput = screen.getByPlaceholderText(
        'list.filter.search.placeholder',
      );

      // Search for "Biba"
      await user.type(searchInput, 'Biba');

      await waitFor(() => {
        expect(screen.getByText('Biba Bobin')).toBeInTheDocument();
        expect(screen.queryByText('Boba Bibin')).not.toBeInTheDocument();
        expect(screen.queryByText('Pupa Lupin')).not.toBeInTheDocument();
        expect(screen.queryByText('Lupa Pupin')).not.toBeInTheDocument();
      });
    });

    it('filters users by last name', async () => {
      const user = userEvent.setup();
      render(<Members project={mockProjectWithMultipleMembers} />, { wrapper });

      const searchInput = screen.getByPlaceholderText(
        'list.filter.search.placeholder',
      );

      // Search for "Bobin"
      await user.type(searchInput, 'Bobin');

      await waitFor(() => {
        expect(screen.getByText('Biba Bobin')).toBeInTheDocument();
        expect(screen.queryByText('Boba Bibin')).not.toBeInTheDocument();
        expect(screen.queryByText('Pupa Lupin')).not.toBeInTheDocument();
        expect(screen.queryByText('Lupa Pupin')).not.toBeInTheDocument();
      });
    });

    it('filters users by email', async () => {
      const user = userEvent.setup();
      render(<Members project={mockProjectWithMultipleMembers} />, { wrapper });

      const searchInput = screen.getByPlaceholderText(
        'list.filter.search.placeholder',
      );

      // Search for "lupa.pupin"
      await user.type(searchInput, 'lupa.pupin');

      await waitFor(() => {
        expect(screen.getByText('Lupa Pupin')).toBeInTheDocument();
        expect(screen.queryByText('Biba Bobin')).not.toBeInTheDocument();
        expect(screen.queryByText('Boba Bibin')).not.toBeInTheDocument();
        expect(screen.queryByText('Pupa Lupin')).not.toBeInTheDocument();
      });
    });

    it('performs case-insensitive search', async () => {
      const user = userEvent.setup();
      render(<Members project={mockProjectWithMultipleMembers} />, { wrapper });

      const searchInput = screen.getByPlaceholderText(
        'list.filter.search.placeholder',
      );

      // Search for "LUPA" (uppercase)
      await user.type(searchInput, 'LUPA');

      await waitFor(() => {
        expect(screen.getByText('Lupa Pupin')).toBeInTheDocument();
        expect(screen.queryByText('Biba Bobin')).not.toBeInTheDocument();
      });
    });

    it('shows all users when search is cleared', async () => {
      const user = userEvent.setup();
      render(<Members project={mockProjectWithMultipleMembers} />, { wrapper });

      const searchInput = screen.getByPlaceholderText(
        'list.filter.search.placeholder',
      );

      // First search for something
      await user.type(searchInput, 'Biba');

      await waitFor(() => {
        expect(screen.getByText('Biba Bobin')).toBeInTheDocument();
        expect(screen.queryByText('Boba Bibin')).not.toBeInTheDocument();
      });

      // Clear the search
      await user.clear(searchInput);

      await waitFor(() => {
        expect(screen.getByText('Biba Bobin')).toBeInTheDocument();
        expect(screen.getByText('Boba Bibin')).toBeInTheDocument();
        expect(screen.getByText('Pupa Lupin')).toBeInTheDocument();
        expect(screen.getByText('Lupa Pupin')).toBeInTheDocument();
      });
    });

    it('shows no results when no matches found', async () => {
      const user = userEvent.setup();
      render(<Members project={mockProjectWithMultipleMembers} />, { wrapper });

      const searchInput = screen.getByPlaceholderText(
        'list.filter.search.placeholder',
      );

      // Search for something that doesn't exist
      await user.type(searchInput, 'NonExistentUser');

      await waitFor(() => {
        expect(screen.queryByText('Biba Bobin')).not.toBeInTheDocument();
        expect(screen.queryByText('Boba Bibin')).not.toBeInTheDocument();
        expect(screen.queryByText('Pupa Lupin')).not.toBeInTheDocument();
        expect(screen.queryByText('Lupa Pupin')).not.toBeInTheDocument();
      });
    });

    it('filters by partial matches', async () => {
      const user = userEvent.setup();
      render(<Members project={mockProjectWithMultipleMembers} />, { wrapper });

      const searchInput = screen.getByPlaceholderText(
        'list.filter.search.placeholder',
      );

      // Search for "upa" which should match both "Pupa" and "Lupa"
      await user.type(searchInput, 'upa');

      await waitFor(() => {
        expect(screen.getByText('Pupa Lupin')).toBeInTheDocument();
        expect(screen.getByText('Lupa Pupin')).toBeInTheDocument();
        expect(screen.queryByText('Biba Bobin')).not.toBeInTheDocument();
        expect(screen.queryByText('Boba Bibin')).not.toBeInTheDocument();
      });
    });

    it('filters by email domain', async () => {
      const user = userEvent.setup();
      render(<Members project={mockProjectWithMultipleMembers} />, { wrapper });

      const searchInput = screen.getByPlaceholderText(
        'list.filter.search.placeholder',
      );

      // Search for "@company.com" which should match all users
      await user.type(searchInput, '@company.com');

      await waitFor(() => {
        expect(screen.getByText('Biba Bobin')).toBeInTheDocument();
        expect(screen.getByText('Boba Bibin')).toBeInTheDocument();
        expect(screen.getByText('Pupa Lupin')).toBeInTheDocument();
        expect(screen.getByText('Lupa Pupin')).toBeInTheDocument();
      });
    });

    it('maintains search state during component updates', async () => {
      const user = userEvent.setup();
      const { rerender } = render(
        <Members project={mockProjectWithMultipleMembers} />,
        { wrapper },
      );

      const searchInput = screen.getByPlaceholderText(
        'list.filter.search.placeholder',
      );

      // Search for "Boba"
      await user.type(searchInput, 'Boba');

      await waitFor(() => {
        expect(screen.getByText('Boba Bibin')).toBeInTheDocument();
        expect(screen.queryByText('Biba Bobin')).not.toBeInTheDocument();
      });

      // Rerender with same props
      rerender(<Members project={mockProjectWithMultipleMembers} />);

      // Search should still be active
      await waitFor(() => {
        expect(screen.getByText('Boba Bibin')).toBeInTheDocument();
        expect(screen.queryByText('Biba Bobin')).not.toBeInTheDocument();
      });
    });
  });

  describe('Token Refresh on Self-Modification', () => {
    beforeEach(() => {
      vi.clearAllMocks();
      mockUpdate.mockClear();
    });

    it('refreshes token when user removes themselves from project', async () => {
      mockFetchUsers.mockResolvedValue({
        users: [
          {
            id: 'test-user-id',
            firstName: 'Test',
            lastName: 'User',
            email: 'test@example.com',
          },
        ],
      });

      const projectWithCurrentUser = {
        ...mockProjectWithMembers,
        users: [
          {
            id: 'test-user-id',
            firstName: 'Test',
            lastName: 'User',
            role: 'Team Member',
            email: 'test@example.com',
          },
        ],
      };

      const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries');
      mockDeleteUserFromProject.mockImplementation(() => Promise.resolve());

      await act(async () => {
        render(
          <QueryClientProvider client={queryClient}>
            <Members project={projectWithCurrentUser} />
          </QueryClientProvider>,
        );
      });

      const contextMenuButton = screen.getByLabelText('list.actions.label');
      await fireEvent.click(contextMenuButton);

      const deleteButton = screen.getByLabelText(
        'settings.membersAndInvitedUsers.members.actions.remove.label',
      );
      await fireEvent.click(deleteButton);

      const deleteConfirmButton = screen.getByText('actions.confirm.title');
      await fireEvent.click(deleteConfirmButton);

      await waitFor(() => {
        expect(mockDeleteUserFromProject).toHaveBeenCalledWith({
          projectId: '1',
          userId: 'test-user-id',
        });
        expect(mockUpdate).toHaveBeenCalledTimes(1);
      });

      invalidateQueriesSpy.mockRestore();
    });

    it('does not refresh token when user removes someone else from project', async () => {
      // Create a project where current user (test-user-id) is not the one being removed
      const projectWithDifferentUser = {
        ...mockProjectWithMembers,
        users: [
          {
            id: 'different-user-id',
            firstName: 'Different',
            lastName: 'User',
            role: 'Team Member',
            email: 'different@example.com',
          },
        ],
      };

      const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries');
      mockDeleteUserFromProject.mockImplementation(() => Promise.resolve());

      await act(async () => {
        render(
          <QueryClientProvider client={queryClient}>
            <Members project={projectWithDifferentUser} />
          </QueryClientProvider>,
        );
      });

      const contextMenuButton = screen.getByLabelText('list.actions.label');
      await fireEvent.click(contextMenuButton);

      const deleteButton = screen.getByLabelText(
        'settings.membersAndInvitedUsers.members.actions.remove.label',
      );
      await fireEvent.click(deleteButton);

      const deleteConfirmButton = screen.getByText('actions.confirm.title');
      await fireEvent.click(deleteConfirmButton);

      await waitFor(() => {
        expect(mockDeleteUserFromProject).toHaveBeenCalledWith({
          projectId: '1',
          userId: 'different-user-id',
        });
        expect(mockUpdate).not.toHaveBeenCalled();
      });

      invalidateQueriesSpy.mockRestore();
    });

    it('refreshes token when user adds themselves to project', async () => {
      mockFetchUsers.mockResolvedValue({
        users: [
          {
            id: 'test-user-id',
            firstName: 'Test',
            lastName: 'User',
            email: 'test@example.com',
          },
          {
            id: 'user2',
            firstName: 'User',
            lastName: 'Two',
            email: 'user2@company.com',
          },
        ],
      });

      mockFetchInvitedUsers.mockResolvedValue({
        invitedUsers: [],
      });

      await act(async () => {
        render(<Members project={mockProjectWithMembers} />, { wrapper });
      });

      const addButton = screen.getByLabelText(
        'settings.membersAndInvitedUsers.members.actions.add',
      );
      await waitFor(() => expect(addButton).not.toBeDisabled());
      fireEvent.click(addButton);

      fireEvent.click(
        screen.getAllByLabelText(
          'settings.membersAndInvitedUsers.members.actions.add.form.users.label',
        )[1],
      );
      fireEvent.click(screen.getByRole('option', { name: 'test@example.com' }));

      const confirmButton = screen.getByText(
        'settings.membersAndInvitedUsers.members.actions.add.modal.confirm',
      );
      fireEvent.click(confirmButton);

      await waitFor(() => {
        expect(mockAddUsersToProject).toHaveBeenCalledWith({
          projectId: '1',
          userIds: ['test-user-id'],
        });
        expect(mockUpdate).toHaveBeenCalledTimes(1);
      });
    });

    it('does not refresh token when user adds others to project', async () => {
      mockFetchUsers.mockResolvedValue({
        users: [
          {
            id: 'test-user-id',
            firstName: 'Test',
            lastName: 'User',
            email: 'test@example.com',
          },
          {
            id: 'user2',
            firstName: 'User',
            lastName: 'Two',
            email: 'user2@company.com',
          },
        ],
      });

      mockFetchInvitedUsers.mockResolvedValue({
        invitedUsers: [],
      });

      await act(async () => {
        render(<Members project={mockProjectWithMembers} />, { wrapper });
      });

      const addButton = screen.getByLabelText(
        'settings.membersAndInvitedUsers.members.actions.add',
      );
      await waitFor(() => expect(addButton).not.toBeDisabled());
      fireEvent.click(addButton);

      fireEvent.click(
        screen.getAllByLabelText(
          'settings.membersAndInvitedUsers.members.actions.add.form.users.label',
        )[1],
      );
      fireEvent.click(
        screen.getByRole('option', { name: 'user2@company.com' }),
      );

      const confirmButton = screen.getByText(
        'settings.membersAndInvitedUsers.members.actions.add.modal.confirm',
      );
      fireEvent.click(confirmButton);

      await waitFor(() => {
        expect(mockAddUsersToProject).toHaveBeenCalledWith({
          projectId: '1',
          userIds: ['user2'],
        });
        expect(mockUpdate).not.toHaveBeenCalled();
      });
    });
  });

  describe('Error Handling', () => {
    beforeEach(() => {
      vi.clearAllMocks();
    });

    it('shows error toast when removing user fails', async () => {
      const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries');
      mockDeleteUserFromProject.mockImplementation(() =>
        Promise.reject(new Error('Delete failed')),
      );

      await act(async () => {
        render(
          <QueryClientProvider client={queryClient}>
            <Members project={mockProjectWithMembers} />
          </QueryClientProvider>,
        );
      });

      const contextMenuButton = screen.getByLabelText('list.actions.label');
      await fireEvent.click(contextMenuButton);

      const deleteButton = screen.getByLabelText(
        'settings.membersAndInvitedUsers.members.actions.remove.label',
      );
      await fireEvent.click(deleteButton);

      const deleteConfirmButton = screen.getByText('actions.confirm.title');
      await fireEvent.click(deleteConfirmButton);

      await waitFor(() => {
        expect(mockDeleteUserFromProject).toHaveBeenCalledWith({
          projectId: '1',
          userId: 'user1',
        });
        expect(toastErrorMock).toBeCalledWith(
          'settings.membersAndInvitedUsers.members.actions.remove.notification.error',
        );
        expect(invalidateQueriesSpy).not.toHaveBeenCalled();
      });

      invalidateQueriesSpy.mockRestore();
    });

    it('shows error toast when adding users fails', async () => {
      mockFetchUsers.mockResolvedValue({
        users: [
          {
            id: 'user2',
            firstName: 'User',
            lastName: 'Two',
            email: 'user2@company.com',
          },
        ],
      });

      mockFetchInvitedUsers.mockResolvedValue({
        invitedUsers: [],
      });

      mockAddUsersToProject.mockImplementation(() =>
        Promise.reject(new Error('Add failed')),
      );

      await act(async () => {
        render(<Members project={mockProjectWithMembers} />, { wrapper });
      });

      const addButton = screen.getByLabelText(
        'settings.membersAndInvitedUsers.members.actions.add',
      );
      await waitFor(() => expect(addButton).not.toBeDisabled());
      fireEvent.click(addButton);

      fireEvent.click(
        screen.getAllByLabelText(
          'settings.membersAndInvitedUsers.members.actions.add.form.users.label',
        )[1],
      );
      fireEvent.click(
        screen.getByRole('option', { name: 'user2@company.com' }),
      );

      const confirmButton = screen.getByText(
        'settings.membersAndInvitedUsers.members.actions.add.modal.confirm',
      );
      fireEvent.click(confirmButton);

      await waitFor(() => {
        expect(mockAddUsersToProject).toHaveBeenCalledWith({
          projectId: '1',
          userIds: ['user2'],
        });
        expect(toastErrorMock).toBeCalledWith(
          'settings.membersAndInvitedUsers.members.actions.add.notification.error',
        );
      });
    });

    it('does not refresh token when user removal fails', async () => {
      mockFetchUsers.mockResolvedValue({
        users: [
          {
            id: 'test-user-id',
            firstName: 'Test',
            lastName: 'User',
            email: 'test@example.com',
          },
        ],
      });

      const projectWithCurrentUser = {
        ...mockProjectWithMembers,
        users: [
          {
            id: 'test-user-id',
            firstName: 'Test',
            lastName: 'User',
            role: 'Team Member',
            email: 'test@example.com',
          },
        ],
      };

      mockDeleteUserFromProject.mockImplementation(() =>
        Promise.reject(new Error('Delete failed')),
      );

      await act(async () => {
        render(
          <QueryClientProvider client={queryClient}>
            <Members project={projectWithCurrentUser} />
          </QueryClientProvider>,
        );
      });

      const contextMenuButton = screen.getByLabelText('list.actions.label');
      await fireEvent.click(contextMenuButton);

      const deleteButton = screen.getByLabelText(
        'settings.membersAndInvitedUsers.members.actions.remove.label',
      );
      await fireEvent.click(deleteButton);

      const deleteConfirmButton = screen.getByText('actions.confirm.title');
      await fireEvent.click(deleteConfirmButton);

      await waitFor(() => {
        expect(mockDeleteUserFromProject).toHaveBeenCalledWith({
          projectId: '1',
          userId: 'test-user-id',
        });
        expect(mockUpdate).not.toHaveBeenCalled();
        expect(toastErrorMock).toBeCalledWith(
          'settings.membersAndInvitedUsers.members.actions.remove.notification.error',
        );
      });
    });

    it('does not refresh token when user addition fails', async () => {
      mockFetchUsers.mockResolvedValue({
        users: [
          {
            id: 'test-user-id',
            firstName: 'Test',
            lastName: 'User',
            email: 'test@example.com',
          },
        ],
      });

      mockFetchInvitedUsers.mockResolvedValue({
        invitedUsers: [],
      });

      mockAddUsersToProject.mockImplementation(() =>
        Promise.reject(new Error('Add failed')),
      );

      await act(async () => {
        render(<Members project={mockProjectWithMembers} />, { wrapper });
      });

      const addButton = screen.getByLabelText(
        'settings.membersAndInvitedUsers.members.actions.add',
      );
      await waitFor(() => expect(addButton).not.toBeDisabled());
      fireEvent.click(addButton);

      fireEvent.click(
        screen.getAllByLabelText(
          'settings.membersAndInvitedUsers.members.actions.add.form.users.label',
        )[1],
      );
      fireEvent.click(screen.getByRole('option', { name: 'test@example.com' }));

      const confirmButton = screen.getByText(
        'settings.membersAndInvitedUsers.members.actions.add.modal.confirm',
      );
      fireEvent.click(confirmButton);

      await waitFor(() => {
        expect(mockAddUsersToProject).toHaveBeenCalledWith({
          projectId: '1',
          userIds: ['test-user-id'],
        });
        expect(mockUpdate).not.toHaveBeenCalled();
        expect(toastErrorMock).toBeCalledWith(
          'settings.membersAndInvitedUsers.members.actions.add.notification.error',
        );
      });
    });
  });
});
