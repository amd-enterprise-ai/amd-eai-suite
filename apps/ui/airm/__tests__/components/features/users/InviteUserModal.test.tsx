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

import { fetchProjects } from '@/services/app';
import { fetchInvitedUsers, fetchUsers, inviteUser } from '@/services/app';
import { useAccessControl } from '@/hooks/useAccessControl';

import { APIRequestError } from '@amdenterpriseai/utils/app';

import { UserRole } from '@amdenterpriseai/types';

import InviteUserModal from '@/components/features/users/InviteUserModal';

import wrapper from '@/__tests__/ProviderWrapper';
import { Mock, vi } from 'vitest';
import {
  mockUsersResponse,
  mockInvitedUsersResponse,
} from '@/__mocks__/services/app/users.data';
import { mockProjectsResponse } from '@/__mocks__/services/app/projects.data';

const toastSuccessMock = vi.fn();
const toastErrorMock = vi.fn();
vi.mock('@amdenterpriseai/hooks', async (importOriginal) => ({
  ...(await importOriginal()),
  useSystemToast: () => {
    const toast = vi.fn() as any;
    toast.success = toastSuccessMock;
    toast.error = toastErrorMock;
    return { toast };
  },
}));

vi.mock('@/services/app', async (importOriginal) => {
  return {
    ...(await importOriginal()),
    inviteUser: vi.fn(),
    fetchUsers: vi.fn(),
    fetchInvitedUsers: vi.fn(),
    fetchProjects: vi.fn(),
  };
});

vi.mock('@/hooks/useAccessControl', () => ({
  useAccessControl: vi.fn(() => ({
    isRoleManagementEnabled: true,
    isInviteEnabled: true,
    isAdministrator: true,
    smtpEnabled: true,
    isTempPasswordRequired: false,
  })),
}));

describe('InviteUserModal', () => {
  const onOpenChange = vi.fn();

  beforeEach(async () => {
    toastSuccessMock.mockClear();
    toastErrorMock.mockClear();
    vi.mocked(fetchUsers).mockResolvedValue(mockUsersResponse);
    vi.mocked(fetchInvitedUsers).mockResolvedValue(mockInvitedUsersResponse);
    vi.mocked(fetchProjects).mockResolvedValue(mockProjectsResponse);

    vi.mocked(useAccessControl).mockReturnValue({
      isRoleManagementEnabled: true,
      isInviteEnabled: true,
      isAdministrator: true,
      smtpEnabled: true,
      isTempPasswordRequired: false,
    });
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
    (inviteUser as Mock).mockResolvedValueOnce({});

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
    await act(async () => {
      await fireEvent.click(actionButton);
    });

    await waitFor(
      () => {
        expect(inviteUser).toHaveBeenCalledWith(
          {
            email: 'newuser@example.com',
            roles: [UserRole.PLATFORM_ADMIN],
            project_ids: [],
            temporary_password: undefined,
          },
          expect.any(Object),
        );
      },
      { timeout: 5000 },
    );
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

    await waitFor(
      () => {
        expect(inviteUser).toHaveBeenCalledWith(
          {
            email: 'newuser@example.com',
            roles: [UserRole.PLATFORM_ADMIN],
            project_ids: [],
            temporary_password: undefined,
          },
          expect.any(Object),
        );
      },
      { timeout: 3000 },
    );
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
      expect(inviteUser).toHaveBeenCalledWith(
        {
          email: 'newuser@example.com',
          roles: [],
          project_ids: [],
          temporary_password: undefined,
        },
        expect.any(Object),
      );
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
      target: { value: 'USER1@amd.com' },
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
      target: { value: 'INVITED1@amd.com' },
    });
    const actionButton = screen.getByText('modal.addUser.actions.confirm');
    fireEvent.click(actionButton);

    const format = await screen.findByText(
      'modal.addUser.form.email.validation.unique',
    );
    expect(format).toBeTruthy();
  });

  it('Able invite a user to a project if the project is supplied as input', async () => {
    (fetchProjects as Mock).mockResolvedValueOnce(mockProjectsResponse);

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
      await fireEvent.click(screen.getByTestId('project-project-1'));
    });

    const actionButton = screen.getByText('modal.addUser.actions.confirm');
    await fireEvent.click(actionButton);

    await waitFor(() => {
      expect(inviteUser).toHaveBeenCalledWith(
        {
          email: 'newuser@example.com',
          roles: ['Platform Administrator'],
          project_ids: ['project-1'],
          temporary_password: undefined,
        },
        expect.any(Object),
      );
    });
  });

  it('calls onSuccess when invite is successful', async () => {
    const onSuccess = vi.fn(); // Mock success callback

    (inviteUser as Mock).mockResolvedValueOnce({});
    (fetchProjects as Mock).mockResolvedValueOnce(mockProjectsResponse);

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
    await fireEvent.click(screen.getByTestId('project-project-1'));

    const actionButton = screen.getByText('modal.addUser.actions.confirm');
    await fireEvent.click(actionButton);

    await waitFor(() => {
      expect(inviteUser).toHaveBeenCalledWith(
        {
          email: 'newuser@example.com',
          roles: [UserRole.PLATFORM_ADMIN],
          project_ids: ['project-1'],
          temporary_password: undefined,
        },
        expect.any(Object),
      );
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  describe('Pre-selected Projects', () => {
    it('includes pre-selected projects when selectedProjectIds is provided', async () => {
      (fetchProjects as Mock).mockResolvedValueOnce(mockProjectsResponse);
      (inviteUser as Mock).mockResolvedValueOnce({});

      await act(async () => {
        render(
          <InviteUserModal
            isOpen={true}
            onOpenChange={onOpenChange}
            selectedProjectIds={['project-1', 'project-2']}
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

      const actionButton = screen.getByText('modal.addUser.actions.confirm');
      await fireEvent.click(actionButton);

      await waitFor(
        () => {
          expect(inviteUser).toHaveBeenCalledWith(
            {
              email: 'newuser@example.com',
              roles: [UserRole.PLATFORM_ADMIN],
              project_ids: ['project-1', 'project-2'],
              temporary_password: undefined,
            },
            expect.any(Object),
          );
        },
        { timeout: 3000 },
      );
    });

    it('includes pre-selected project when single selectedProjectId is provided', async () => {
      (inviteUser as Mock).mockResolvedValueOnce({});
      (fetchProjects as Mock).mockResolvedValueOnce(mockProjectsResponse);

      await act(async () => {
        render(
          <InviteUserModal
            isOpen={true}
            onOpenChange={onOpenChange}
            selectedProjectIds={['project-1']}
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

      const actionButton = screen.getByText('modal.addUser.actions.confirm');
      await fireEvent.click(actionButton);

      await waitFor(() => {
        expect(inviteUser).toHaveBeenCalledWith(
          {
            email: 'newuser@example.com',
            roles: [UserRole.PLATFORM_ADMIN],
            project_ids: ['project-1'],
            temporary_password: undefined,
          },
          expect.any(Object),
        );
      });
    });

    it('includes pre-selected projects with Team Member role', async () => {
      (inviteUser as Mock).mockResolvedValueOnce({});
      (fetchProjects as Mock).mockResolvedValueOnce(mockProjectsResponse);

      await act(async () => {
        render(
          <InviteUserModal
            isOpen={true}
            onOpenChange={onOpenChange}
            selectedProjectIds={['project-1']}
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

      const selectTrigger = screen.getAllByLabelText(
        'modal.addUser.form.roles.label',
      );
      await fireEvent.click(selectTrigger[1]);

      const selectOption = screen.getAllByText(
        'modal.addUser.form.roles.options.teamMember',
      );
      await fireEvent.click(selectOption[1]);

      const actionButton = screen.getByText('modal.addUser.actions.confirm');
      await fireEvent.click(actionButton);

      await waitFor(() => {
        expect(inviteUser).toHaveBeenCalledWith(
          {
            email: 'newuser@example.com',
            roles: [],
            project_ids: ['project-1'],
            temporary_password: undefined,
          },
          expect.any(Object),
        );
      });
    });

    it('allows user to add more projects to pre-selected ones', async () => {
      (inviteUser as Mock).mockResolvedValueOnce({});
      (fetchProjects as Mock).mockResolvedValueOnce(mockProjectsResponse);

      await act(async () => {
        render(
          <InviteUserModal
            isOpen={true}
            onOpenChange={onOpenChange}
            selectedProjectIds={['project-1']}
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
      await fireEvent.click(screen.getByTestId('project-project-2'));

      const actionButton = screen.getByText('modal.addUser.actions.confirm');
      await fireEvent.click(actionButton);

      await waitFor(() => {
        expect(inviteUser).toHaveBeenCalledWith(
          {
            email: 'newuser@example.com',
            roles: [UserRole.PLATFORM_ADMIN],
            project_ids: expect.arrayContaining(['project-1', 'project-2']),
            temporary_password: undefined,
          },
          expect.any(Object),
        );
      });
    });

    it('calls onSuccess callback when invite with pre-selected projects succeeds', async () => {
      const onSuccess = vi.fn();
      (inviteUser as Mock).mockResolvedValueOnce({});
      (fetchProjects as Mock).mockResolvedValueOnce(mockProjectsResponse);

      await act(async () => {
        render(
          <InviteUserModal
            isOpen={true}
            onOpenChange={onOpenChange}
            selectedProjectIds={['project-1']}
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

      const actionButton = screen.getByText('modal.addUser.actions.confirm');
      await fireEvent.click(actionButton);

      await waitFor(() => {
        expect(inviteUser).toHaveBeenCalledWith(
          {
            email: 'newuser@example.com',
            roles: [UserRole.PLATFORM_ADMIN],
            project_ids: ['project-1'],
            temporary_password: undefined,
          },
          expect.any(Object),
        );
        expect(onSuccess).toHaveBeenCalled();
      });
    });

    it('handles empty selectedProjectIds array', async () => {
      (inviteUser as Mock).mockResolvedValueOnce({});
      (fetchProjects as Mock).mockResolvedValueOnce(mockProjectsResponse);

      await act(async () => {
        render(
          <InviteUserModal
            isOpen={true}
            onOpenChange={onOpenChange}
            selectedProjectIds={[]}
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

      const actionButton = screen.getByText('modal.addUser.actions.confirm');
      await fireEvent.click(actionButton);

      await waitFor(() => {
        expect(inviteUser).toHaveBeenCalledWith(
          {
            email: 'newuser@example.com',
            roles: [UserRole.PLATFORM_ADMIN],
            project_ids: [],
            temporary_password: undefined,
          },
          expect.any(Object),
        );
      });
    });

    it('includes pre-selected projects with temporary password', async () => {
      vi.mocked(useAccessControl).mockReturnValue({
        isRoleManagementEnabled: true,
        isInviteEnabled: true,
        isAdministrator: true,
        smtpEnabled: true,
        isTempPasswordRequired: true,
      });

      (inviteUser as Mock).mockResolvedValueOnce({});
      (fetchProjects as Mock).mockResolvedValueOnce(mockProjectsResponse);

      await act(async () => {
        render(
          <InviteUserModal
            isOpen={true}
            onOpenChange={onOpenChange}
            selectedProjectIds={['project-1', 'project-2']}
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

      await fireEvent.change(
        screen.getByLabelText('modal.addUser.form.tempPassword.label'),
        {
          target: { value: 'TempPassword123' },
        },
      );

      await waitFor(() => {
        expect(vi.mocked(fetchProjects)).toBeCalled();
      });

      const actionButton = screen.getByText('modal.addUser.actions.confirm');
      await fireEvent.click(actionButton);

      await waitFor(() => {
        expect(inviteUser).toHaveBeenCalledWith(
          {
            email: 'newuser@example.com',
            roles: [UserRole.PLATFORM_ADMIN],
            project_ids: ['project-1', 'project-2'],
            temporary_password: 'TempPassword123',
          },
          expect.any(Object),
        );
      });
    });
  });

  describe('Temporary Password', () => {
    it('does not show temporary password field when not required', async () => {
      vi.mocked(useAccessControl).mockReturnValue({
        isRoleManagementEnabled: true,
        isInviteEnabled: true,
        isAdministrator: true,
        smtpEnabled: true,
        isTempPasswordRequired: false,
      });

      await act(async () => {
        render(<InviteUserModal isOpen={true} onOpenChange={onOpenChange} />, {
          wrapper,
        });
      });

      const tempPasswordField = screen.queryByLabelText(
        'modal.addUser.form.tempPassword.label',
      );
      expect(tempPasswordField).not.toBeInTheDocument();
    });

    it('shows temporary password field when required', async () => {
      vi.mocked(useAccessControl).mockReturnValue({
        isRoleManagementEnabled: true,
        isInviteEnabled: true,
        isAdministrator: true,
        smtpEnabled: true,
        isTempPasswordRequired: true,
      });

      await act(async () => {
        render(<InviteUserModal isOpen={true} onOpenChange={onOpenChange} />, {
          wrapper,
        });
      });

      const tempPasswordField = screen.getByLabelText(
        'modal.addUser.form.tempPassword.label',
      );
      expect(tempPasswordField).toBeInTheDocument();
    });

    it('validates temporary password minimum length', async () => {
      vi.mocked(useAccessControl).mockReturnValue({
        isRoleManagementEnabled: true,
        isInviteEnabled: true,
        isAdministrator: true,
        smtpEnabled: true,
        isTempPasswordRequired: true,
      });

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

      await fireEvent.change(
        screen.getByLabelText('modal.addUser.form.tempPassword.label'),
        {
          target: { value: 'short' }, // Less than 8 characters
        },
      );

      const actionButton = screen.getByText('modal.addUser.actions.confirm');
      await fireEvent.click(actionButton);

      const errorMessage = await screen.findByText(
        'modal.addUser.form.tempPassword.validation.minLength',
      );
      expect(errorMessage).toBeInTheDocument();
    });

    it('validates temporary password maximum length', async () => {
      vi.mocked(useAccessControl).mockReturnValue({
        isRoleManagementEnabled: true,
        isInviteEnabled: true,
        isAdministrator: true,
        smtpEnabled: true,
        isTempPasswordRequired: true,
      });

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

      // Create a password longer than 256 characters
      const longPassword = 'a'.repeat(257);
      await fireEvent.change(
        screen.getByLabelText('modal.addUser.form.tempPassword.label'),
        {
          target: { value: longPassword },
        },
      );

      const actionButton = screen.getByText('modal.addUser.actions.confirm');
      await fireEvent.click(actionButton);

      const errorMessage = await screen.findByText(
        'modal.addUser.form.tempPassword.validation.maxLength',
      );
      expect(errorMessage).toBeInTheDocument();
    });

    it('accepts valid temporary password (8-256 characters)', async () => {
      (inviteUser as Mock).mockResolvedValueOnce({});

      vi.mocked(useAccessControl).mockReturnValue({
        isRoleManagementEnabled: true,
        isInviteEnabled: true,
        isAdministrator: true,
        smtpEnabled: true,
        isTempPasswordRequired: true,
      });

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

      await fireEvent.change(
        screen.getByLabelText('modal.addUser.form.tempPassword.label'),
        {
          target: { value: 'ValidPass123' }, // Valid password
        },
      );

      const actionButton = screen.getByText('modal.addUser.actions.confirm');
      await fireEvent.click(actionButton);

      await waitFor(
        () => {
          expect(inviteUser).toHaveBeenCalledWith(
            {
              email: 'newuser@example.com',
              roles: [UserRole.PLATFORM_ADMIN],
              project_ids: [],
              temporary_password: 'ValidPass123',
            },
            expect.any(Object),
          );
        },
        { timeout: 3000 },
      );
    });

    it('includes temporary password in API call when provided', async () => {
      vi.mocked(useAccessControl).mockReturnValue({
        isRoleManagementEnabled: true,
        isInviteEnabled: true,
        isAdministrator: true,
        smtpEnabled: true,
        isTempPasswordRequired: true,
      });

      (inviteUser as Mock).mockResolvedValueOnce({});

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

      await fireEvent.change(
        screen.getByLabelText('modal.addUser.form.tempPassword.label'),
        {
          target: { value: 'TempPassword123' },
        },
      );

      const actionButton = screen.getByText('modal.addUser.actions.confirm');
      await fireEvent.click(actionButton);

      await waitFor(() => {
        expect(inviteUser).toHaveBeenCalledWith(
          expect.objectContaining({
            email: 'newuser@example.com',
            temporary_password: 'TempPassword123',
          }),
          expect.any(Object),
        );
      });
    });

    it('invites user with Team Member role and temporary password', async () => {
      vi.mocked(useAccessControl).mockReturnValue({
        isRoleManagementEnabled: true,
        isInviteEnabled: true,
        isAdministrator: true,
        smtpEnabled: true,
        isTempPasswordRequired: true,
      });

      (inviteUser as Mock).mockResolvedValueOnce({});

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
      await fireEvent.click(selectTrigger[1]);

      const selectOption = screen.getAllByText(
        'modal.addUser.form.roles.options.teamMember',
      );
      await fireEvent.click(selectOption[1]);

      await fireEvent.change(
        screen.getByLabelText('modal.addUser.form.tempPassword.label'),
        {
          target: { value: 'TempPassword123' },
        },
      );

      const actionButton = screen.getByText('modal.addUser.actions.confirm');
      await fireEvent.click(actionButton);

      await waitFor(() => {
        expect(inviteUser).toHaveBeenCalledWith(
          {
            email: 'newuser@example.com',
            roles: [],
            project_ids: [],
            temporary_password: 'TempPassword123',
          },
          expect.any(Object),
        );
      });
    });

    it('rejects temporary password with leading space', async () => {
      vi.mocked(useAccessControl).mockReturnValue({
        isRoleManagementEnabled: true,
        isInviteEnabled: true,
        isAdministrator: true,
        smtpEnabled: true,
        isTempPasswordRequired: true,
      });

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

      await fireEvent.change(
        screen.getByLabelText('modal.addUser.form.tempPassword.label'),
        {
          target: { value: ' ValidPass123' }, // Leading space
        },
      );

      const actionButton = screen.getByText('modal.addUser.actions.confirm');
      await fireEvent.click(actionButton);

      const errorMessage = await screen.findByText(
        'modal.addUser.form.tempPassword.validation.noLeadingTrailingSpaces',
      );
      expect(errorMessage).toBeInTheDocument();
      expect(inviteUser).not.toHaveBeenCalled();
    });

    it('rejects temporary password with trailing space', async () => {
      vi.mocked(useAccessControl).mockReturnValue({
        isRoleManagementEnabled: true,
        isInviteEnabled: true,
        isAdministrator: true,
        smtpEnabled: true,
        isTempPasswordRequired: true,
      });

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

      await fireEvent.change(
        screen.getByLabelText('modal.addUser.form.tempPassword.label'),
        {
          target: { value: 'ValidPass123 ' }, // Trailing space
        },
      );

      const actionButton = screen.getByText('modal.addUser.actions.confirm');
      await fireEvent.click(actionButton);

      const errorMessage = await screen.findByText(
        'modal.addUser.form.tempPassword.validation.noLeadingTrailingSpaces',
      );
      expect(errorMessage).toBeInTheDocument();
      expect(inviteUser).not.toHaveBeenCalled();
    });

    it('rejects temporary password with both leading and trailing spaces', async () => {
      vi.mocked(useAccessControl).mockReturnValue({
        isRoleManagementEnabled: true,
        isInviteEnabled: true,
        isAdministrator: true,
        smtpEnabled: true,
        isTempPasswordRequired: true,
      });

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

      await fireEvent.change(
        screen.getByLabelText('modal.addUser.form.tempPassword.label'),
        {
          target: { value: '  ValidPass123  ' }, // Both leading and trailing spaces
        },
      );

      const actionButton = screen.getByText('modal.addUser.actions.confirm');
      await fireEvent.click(actionButton);

      const errorMessage = await screen.findByText(
        'modal.addUser.form.tempPassword.validation.noLeadingTrailingSpaces',
      );
      expect(errorMessage).toBeInTheDocument();
      expect(inviteUser).not.toHaveBeenCalled();
    });

    it('accepts temporary password with spaces in the middle', async () => {
      (inviteUser as Mock).mockResolvedValueOnce({});

      vi.mocked(useAccessControl).mockReturnValue({
        isRoleManagementEnabled: true,
        isInviteEnabled: true,
        isAdministrator: true,
        smtpEnabled: true,
        isTempPasswordRequired: true,
      });

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

      await fireEvent.change(
        screen.getByLabelText('modal.addUser.form.tempPassword.label'),
        {
          target: { value: 'Valid Pass 123' }, // Spaces in the middle are OK
        },
      );

      const actionButton = screen.getByText('modal.addUser.actions.confirm');
      await fireEvent.click(actionButton);

      await waitFor(() => {
        expect(inviteUser).toHaveBeenCalledWith(
          {
            email: 'newuser@example.com',
            roles: [UserRole.PLATFORM_ADMIN],
            project_ids: [],
            temporary_password: 'Valid Pass 123',
          },
          expect.any(Object),
        );
      });
    });
  });
});
