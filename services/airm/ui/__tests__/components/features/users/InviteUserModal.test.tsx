// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';

import { fetchProjects } from '@/services/app/projects';
import {
  fetchInvitedUsers,
  fetchUsers,
  inviteUser,
} from '@/services/app/users';

import { APIRequestError } from '@/utils/app/errors';

import { UserRole } from '@/types/enums/user-roles';

import InviteUserModal from '@/components/features/users/InviteUserModal';

import wrapper from '@/__tests__/ProviderWrapper';
import { Mock, vi } from 'vitest';

const toastSuccessMock = vi.fn();
const toastErrorMock = vi.fn();
vi.mock('@/hooks/useSystemToast', () => {
  const useSystemToast = () => {
    const toast = vi.fn() as any;
    toast.success = toastSuccessMock;
    toast.error = toastErrorMock;
    return { toast };
  };
  return { default: useSystemToast, useSystemToast };
});

const usersData = {
  users: [
    {
      id: '1',
      email: 'existing@example.com',
      firstName: 'John',
      lastName: 'Doe',
      role: UserRole.PLATFORM_ADMIN,
      projects: [
        {
          id: '1',
          name: 'default',
          description: 'Default Project',
        },
        {
          id: '2',
          name: 'test',
          description: 'Another project',
        },
      ],
    },
  ],
};

const invitedUsersData = {
  invitedUsers: [
    {
      id: 2,
      email: 'existing-invite@example.com',
      role: UserRole.PLATFORM_ADMIN,
      projects: null,
    },
  ],
};

const projectsData = {
  projects: [
    {
      id: '1',
      name: 'default',
      description: 'Default Project',
    },
    {
      id: '2',
      name: 'test',
      description: 'Test Project',
    },
  ],
};

vi.mock('@/services/app/users', async (importOriginal) => {
  return {
    ...(await importOriginal()),
    inviteUser: vi.fn(),
    fetchUsers: vi.fn(),
    fetchInvitedUsers: vi.fn(),
  };
});

vi.mock('@/services/app/projects', async (importOriginal) => {
  return {
    ...(await importOriginal()),
    fetchProjects: vi.fn(),
  };
});

describe('InviteUserModal', () => {
  const onOpenChange = vi.fn();

  beforeEach(() => {
    toastSuccessMock.mockClear();
    toastErrorMock.mockClear();
    vi.mocked(fetchUsers).mockResolvedValue(usersData);
    vi.mocked(fetchInvitedUsers).mockResolvedValue(invitedUsersData);
    vi.mocked(fetchProjects).mockResolvedValue(projectsData);
  });

  it('renders the modal form', () => {
    act(() => {
      render(<InviteUserModal isOpen={true} onOpenChange={onOpenChange} />, {
        wrapper,
      });
    });

    expect(screen.getByText('modal.addUser.title')).toBeInTheDocument();
  });

  it('validates email is required', async () => {
    await act(() => {
      render(<InviteUserModal isOpen={true} onOpenChange={onOpenChange} />, {
        wrapper,
      });
    });

    await act(() => {
      fireEvent.change(
        screen.getByLabelText('modal.addUser.form.email.label'),
        {
          target: { value: 'newuser@example.com' },
        },
      );
    });

    await act(() => {
      fireEvent.change(
        screen.getByLabelText('modal.addUser.form.email.label'),
        {
          target: { value: '' },
        },
      );
    });

    await act(() => {
      const actionButton = screen.getByText('modal.addUser.actions.confirm');
      fireEvent.click(actionButton);
    });

    const errorMessage = await screen.findByText(
      'modal.addUser.form.email.validation.required',
    );

    expect(errorMessage).toBeInTheDocument();
  });

  it('validates email format', async () => {
    await act(() => {
      render(<InviteUserModal isOpen={true} onOpenChange={onOpenChange} />, {
        wrapper,
      });
    });

    await act(() => {
      fireEvent.change(
        screen.getByLabelText('modal.addUser.form.email.label'),
        {
          target: { value: 'invalid-email' },
        },
      );
    });

    await act(() => {
      const actionButton = screen.getByText('modal.addUser.actions.confirm');
      fireEvent.click(actionButton);
    });

    const format = screen.findByText(
      'modal.addUser.form.email.validation.format',
    );
    expect(format).toBeTruthy();
  });

  it('calls inviteUser on form success', async () => {
    await act(async () => {
      render(<InviteUserModal isOpen={true} onOpenChange={onOpenChange} />, {
        wrapper,
      });
    });

    await fireEvent.change(
      screen.getByLabelText('modal.addUser.form.email.label'),
      {
        target: { value: 'newuser@example.com' },
      },
    );
    const actionButton = screen.getByText('modal.addUser.actions.confirm');
    await fireEvent.click(actionButton);

    await waitFor(() => {
      expect(inviteUser).toHaveBeenCalledWith({
        email: 'newuser@example.com',
        roles: [UserRole.PLATFORM_ADMIN],
        project_ids: [],
      });
      expect(toastSuccessMock).toBeCalledWith(
        'modal.addUser.notification.success',
      );
    });
  });

  it('calls inviteUser on form error', async () => {
    const mockError = new APIRequestError('test error', 400);
    (inviteUser as Mock).mockRejectedValueOnce(mockError);
    await act(async () => {
      render(<InviteUserModal isOpen={true} onOpenChange={onOpenChange} />, {
        wrapper,
      });
    });

    await fireEvent.change(
      screen.getByLabelText('modal.addUser.form.email.label'),
      {
        target: { value: 'newuser@example.com' },
      },
    );
    const actionButton = screen.getByText('modal.addUser.actions.confirm');
    await fireEvent.click(actionButton);

    await waitFor(() => {
      expect(inviteUser).toHaveBeenCalledWith({
        email: 'newuser@example.com',
        roles: [UserRole.PLATFORM_ADMIN],
        project_ids: [],
      });
      expect(toastErrorMock).toBeCalledWith(
        'modal.addUser.notification.error',
        mockError,
      );
    });
  });

  it('team member is selected and no roles is passed over', async () => {
    await act(async () => {
      render(<InviteUserModal isOpen={true} onOpenChange={onOpenChange} />, {
        wrapper,
      });
    });

    await fireEvent.change(
      screen.getByLabelText('modal.addUser.form.email.label'),
      {
        target: { value: 'newuser@example.com' },
      },
    );

    const selectTrigger = screen.getAllByLabelText(
      'modal.addUser.form.roles.label',
    );

    expect(selectTrigger[1]).toBeInTheDocument();

    await fireEvent.click(selectTrigger[1]);

    const selectOption = screen.getAllByText(
      'modal.addUser.form.roles.options.teamMember',
    );

    await fireEvent.click(selectOption[1]);

    const actionButton = screen.getByText('modal.addUser.actions.confirm');
    await fireEvent.click(actionButton);

    await waitFor(() => {
      expect(inviteUser).toHaveBeenCalledWith({
        email: 'newuser@example.com',
        roles: [],
        project_ids: [],
      });
    });
  });

  it('validates email uniqueness for active user', async () => {
    await act(() => {
      render(<InviteUserModal isOpen={true} onOpenChange={onOpenChange} />, {
        wrapper,
      });
    });

    await waitFor(() => {
      expect(vi.mocked(fetchUsers)).toBeCalled();
      expect(vi.mocked(fetchInvitedUsers)).toBeCalled();
    });

    fireEvent.change(screen.getByLabelText('modal.addUser.form.email.label'), {
      target: { value: 'EXIsTING@example.com' },
    });
    const actionButton = screen.getByText('modal.addUser.actions.confirm');
    fireEvent.click(actionButton);

    const format = await screen.findByText(
      'modal.addUser.form.email.validation.unique',
    );
    expect(format).toBeTruthy();
  });

  it('validates email uniqueness for invited user', async () => {
    await act(() => {
      render(<InviteUserModal isOpen={true} onOpenChange={onOpenChange} />, {
        wrapper,
      });
    });

    await waitFor(() => {
      expect(vi.mocked(fetchUsers)).toBeCalled();
      expect(vi.mocked(fetchInvitedUsers)).toBeCalled();
    });

    fireEvent.change(screen.getByLabelText('modal.addUser.form.email.label'), {
      target: { value: 'EXISTING-invite@example.com' },
    });
    const actionButton = screen.getByText('modal.addUser.actions.confirm');
    fireEvent.click(actionButton);

    const format = await screen.findByText(
      'modal.addUser.form.email.validation.unique',
    );
    expect(format).toBeTruthy();
  });

  it('Able invite a user to a project if the project is supplied as input', async () => {
    (fetchProjects as Mock).mockResolvedValueOnce(projectsData);

    await act(async () => {
      render(<InviteUserModal isOpen={true} onOpenChange={onOpenChange} />, {
        wrapper,
      });
    });

    await fireEvent.change(
      screen.getByLabelText('modal.addUser.form.email.label'),
      {
        target: { value: 'newuser@example.com' },
      },
    );

    const selectTrigger = screen.getAllByLabelText(
      'modal.addUser.form.roles.label',
    );

    // wait for hook to be called or else select compnent will not be rendered with list of projects
    await waitFor(() => {
      expect(fetchProjects).toHaveBeenCalled();
    });

    await fireEvent.click(screen.getByTestId('project-select'));

    await waitFor(async () => {
      await fireEvent.click(screen.getByTestId('project-1'));
    });

    const actionButton = screen.getByText('modal.addUser.actions.confirm');
    await fireEvent.click(actionButton);

    await waitFor(() => {
      expect(inviteUser).toHaveBeenCalledWith({
        email: 'newuser@example.com',
        roles: ['Platform Administrator'],
        project_ids: ['1'],
      });
    });
  });

  it('calls onSuccess when invite is successful', async () => {
    const onSuccess = vi.fn(); // Mock success callback

    (inviteUser as Mock).mockResolvedValueOnce({});
    (fetchProjects as Mock).mockResolvedValueOnce(projectsData);

    await act(async () => {
      render(
        <InviteUserModal
          isOpen={true}
          onOpenChange={onOpenChange}
          onSuccess={onSuccess}
        />,
        { wrapper },
      );
    });

    await fireEvent.change(
      screen.getByLabelText('modal.addUser.form.email.label'),
      {
        target: { value: 'newuser@example.com' },
      },
    );

    await waitFor(() => {
      expect(vi.mocked(fetchProjects)).toBeCalled();
    });

    await fireEvent.click(screen.getByTestId('project-select'));
    await fireEvent.click(screen.getByTestId('project-1'));

    const actionButton = screen.getByText('modal.addUser.actions.confirm');
    await fireEvent.click(actionButton);

    await waitFor(() => {
      expect(inviteUser).toHaveBeenCalledWith({
        email: 'newuser@example.com',
        roles: [UserRole.PLATFORM_ADMIN],
        project_ids: ['1'],
      });
      expect(onSuccess).toHaveBeenCalled();
    });
  });
});
