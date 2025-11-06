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
import { SessionProvider } from 'next-auth/react';

import { updateUser } from '@/services/app/users';

import { ClusterStatus } from '@/types/enums/cluster-status';
import { QuotaStatus } from '@/types/enums/quotas';
import { UserRole } from '@/types/enums/user-roles';
import { User, Users, UserWithProjects } from '@/types/users';

import UserPage from '@/pages/users/[id]';

import wrapper from '@/__tests__/ProviderWrapper';
import '@testing-library/jest-dom';
import { Mock } from 'vitest';

const generateMockUsers = (count: number): UserWithProjects[] => {
  return Array.from({ length: count }, (_, i) => ({
    id: (i + 1).toString(),
    firstName: `FirstName ${i + 1}`,
    lastName: `LastName ${i + 1}`,
    email: `user${i + 1}@amd.com`,
    role: UserRole.PLATFORM_ADMIN,
    projects: [],
  }));
};

const mockUser: UserWithProjects = {
  id: '1',
  firstName: 'first',
  lastName: 'last',
  email: 'test@test.com',
  role: UserRole.PLATFORM_ADMIN,
  projects: [],
};

const mockSession = {
  error: null as any,
  expires: '2125-01-01T00:00:00',
  user: {
    id: 'test',
    email: 'testing@test.com',
    roles: [],
  },
};

vi.mock('@/services/app/users', () => ({
  updateUser: vi.fn(),
  deleteUser: vi.fn(),
  assignRoleToUser: vi.fn(),
}));

vi.mock('next/router', () => ({
  useRouter: () => ({
    query: { id: '1' },
    push: vi.fn(),
  }),
}));

describe('user/[id]', () => {
  const mockUpdateUser = updateUser as Mock;

  it('should not crash the page', async () => {
    const mockUser = generateMockUsers(1)[0];
    await act(async () => {
      const { container } = render(
        <SessionProvider session={mockSession}>
          <UserPage user={mockUser} projects={[]} />
        </SessionProvider>,
        { wrapper },
      );
      expect(container).toBeTruthy();
    });
  });

  it('should render user info', async () => {
    const mockUser = generateMockUsers(1)[0];

    await act(async () => {
      render(
        <SessionProvider session={mockSession}>
          <UserPage user={mockUser} projects={[]} />
        </SessionProvider>,
        { wrapper },
      );
    });

    const firstNameField = screen.queryByText('detail.form.firstName.label');
    const lastNameField = screen.queryByText('detail.form.lastName.label');
    const emailField = screen.queryByText('detail.form.email.label');

    expect(
      (firstNameField?.nextElementSibling?.firstChild as HTMLInputElement)
        ?.value,
    ).toBe('FirstName 1');
    expect(
      (lastNameField?.nextElementSibling?.firstChild as HTMLInputElement)
        ?.value,
    ).toBe('LastName 1');
    expect(
      (emailField?.nextElementSibling?.firstChild as HTMLInputElement)?.value,
    ).toBe('user1@amd.com');
  });

  it('validates firstName length', async () => {
    await act(async () => {
      render(
        <SessionProvider session={mockSession}>
          <UserPage user={mockUser} projects={[]} />
        </SessionProvider>,
        { wrapper },
      );
    });

    await act(async () => {
      fireEvent.change(screen.getByLabelText('detail.form.firstName.label'), {
        target: { value: 'a ' },
      });

      const actionButton = screen.getByText('detail.form.actions.submit');
      fireEvent.click(actionButton);
    });

    expect(
      await screen.findByText('detail.form.firstName.validation.length'),
    ).toBeInTheDocument();
  });

  it('validates lastName length', async () => {
    await act(async () => {
      render(
        <SessionProvider session={mockSession}>
          <UserPage user={mockUser} projects={[]} />
        </SessionProvider>,
        { wrapper },
      );
    });

    await act(async () => {
      fireEvent.change(screen.getByLabelText('detail.form.lastName.label'), {
        target: { value: 'a ' },
      });

      const actionButton = screen.getByText('detail.form.actions.submit');
      fireEvent.click(actionButton);
    });

    expect(
      await screen.findByText('detail.form.lastName.validation.length'),
    ).toBeInTheDocument();
  });

  it('calls updateUser on form success (with trimming)', async () => {
    await act(async () => {
      render(
        <SessionProvider session={mockSession}>
          <UserPage user={mockUser} projects={[]} />
        </SessionProvider>,
        { wrapper },
      );
    });

    await act(async () => {
      fireEvent.change(screen.getByLabelText('detail.form.firstName.label'), {
        target: { value: 'New First Name  ' },
      });
      fireEvent.change(screen.getByLabelText('detail.form.lastName.label'), {
        target: { value: 'New Last Name ' },
      });
      const actionButton = screen.getByText('detail.form.actions.submit');
      fireEvent.click(actionButton);
    });

    await waitFor(() => {
      expect(mockUpdateUser).toHaveBeenCalledWith({
        id: '1',
        firstName: 'New First Name',
        lastName: 'New Last Name',
      });
    });
  });
});
