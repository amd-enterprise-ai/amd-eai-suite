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
import { SessionProvider } from 'next-auth/react';

import { assignRoleToUser } from '@/services/app/users';

import { UserRole } from '@/types/enums/user-roles';
import { UserWithProjects } from '@/types/users';

import { UserRoles } from '@/components/features/user';

import wrapper from '@/__tests__/ProviderWrapper';
import { mockSession } from '@/__mocks__/services/app/session.data';
import { Mock } from 'vitest';

const mockUser: UserWithProjects = {
  id: '123',
  firstName: 'Name',
  lastName: 'Last',
  role: UserRole.PLATFORM_ADMIN,
  projects: [],
  email: 'user@user.com',
};

vi.mock('@/services/app/users', () => ({
  assignRoleToUser: vi.fn(),
}));

vi.mock('@/hooks/useAccessControl', () => ({
  useAccessControl: () => ({
    isRoleManagementEnabled: true,
  }),
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

const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <SessionProvider session={mockSession}>
    {wrapper({ children })}
  </SessionProvider>
);

describe('UserRoles', () => {
  const mockAssignRoleToUser = assignRoleToUser as Mock;

  beforeEach(() => {
    toastSuccessMock.mockClear();
    toastErrorMock.mockClear();
  });

  it('renders the component with role name', () => {
    act(() => render(<UserRoles user={mockUser} />, { wrapper: TestWrapper }));

    expect(
      screen.getByText('detail.projectsAndRoles.roles.title'),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        'detail.projectsAndRoles.roles.options.platformAdministrator.name',
      ),
    ).toBeInTheDocument();
  });

  it('renders the component as Team Member if role is null', () => {
    act(() => {
      render(<UserRoles user={{ ...mockUser, role: UserRole.TEAM_MEMBER }} />, {
        wrapper: TestWrapper,
      });
    });
    expect(
      screen.getByText('detail.projectsAndRoles.roles.options.teamMember.name'),
    ).toBeInTheDocument();
  });

  it('calls assignRoleToUserAPI with the correct value when the users role is changed', async () => {
    await act(() =>
      render(<UserRoles user={mockUser} />, { wrapper: TestWrapper }),
    );

    const editButton = screen.getByLabelText(
      'detail.projectsAndRoles.roles.actions.edit',
    );

    await act(() => {
      fireEvent.click(editButton);
    });

    const selectTrigger = screen.getAllByLabelText(
      'detail.projectsAndRoles.roles.form.role.label',
    );

    await act(() => {
      fireEvent.click(selectTrigger[1]);
    });

    const selectOption = screen.getAllByText(
      'detail.projectsAndRoles.roles.form.role.options.teamMember',
    );
    await act(() => {
      fireEvent.click(selectOption[1]);
    });
    const confirmButton = screen.getByText(
      'detail.projectsAndRoles.roles.actions.edit.confirm',
    );
    await act(() => {
      fireEvent.click(confirmButton);
    });
    await waitFor(() => {
      expect(mockAssignRoleToUser).toHaveBeenCalledWith({
        userId: '123',
        role: UserRole.TEAM_MEMBER,
      });
      expect(toastSuccessMock).toBeCalledWith(
        'detail.projectsAndRoles.roles.notification.success',
      );
    });
  });
});
