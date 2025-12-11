// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { mockInvitedUsersResponse } from '@/__mocks__/services/app/users.data';

import { InvitedUsersTab } from '@/components/features/users/InvitedUsersTab';

import wrapper from '@/__tests__/ProviderWrapper';
import '@testing-library/jest-dom';

// Mock next router
vi.mock('next/router', () => ({
  __esModule: true,
  default: {
    push: vi.fn(),
    pathname: '/users',
    query: {},
    asPath: '/users',
  },
}));

// Mock the dependencies
vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = (await importOriginal()) as any;
  return {
    ...actual,
    useQuery: vi.fn(() => ({
      data: mockInvitedUsersResponse,
      isFetching: false,
      isRefetching: false,
      refetch: vi.fn(),
      dataUpdatedAt: new Date(),
    })),
    useMutation: vi.fn(() => ({
      mutate: vi.fn(),
      isPending: false,
    })),
    useQueryClient: vi.fn(() => ({
      invalidateQueries: vi.fn(),
    })),
  };
});

vi.mock('@/hooks/useSystemToast', () => ({
  __esModule: true,
  default: () => ({
    toast: {
      success: vi.fn(),
      error: vi.fn(),
    },
  }),
}));

vi.mock('next-auth/react', () => ({
  useSession: vi.fn(() => ({
    data: { user: { id: '1', email: 'test@example.com' } },
    status: 'authenticated',
  })),
}));

vi.mock('@/hooks/useAccessControl', () => ({
  useAccessControl: vi.fn(() => ({
    isRoleManagementEnabled: true,
    isInviteEnabled: true,
    isAdministrator: true,
    smtpEnabled: true,
    isTempPasswordRequired: false,
  })),
}));

describe('InvitedUsersTab', () => {
  const mockOnInviteUserClick = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render invited users list', () => {
    render(
      <InvitedUsersTab
        initialData={mockInvitedUsersResponse}
        onInviteUserClick={mockOnInviteUserClick}
      />,
      { wrapper },
    );

    mockInvitedUsersResponse.data.forEach((user) => {
      expect(screen.getByText(user.email)).toBeInTheDocument();
    });
  });

  it('should call onInviteUserClick when invite button is clicked', async () => {
    render(
      <InvitedUsersTab
        initialData={mockInvitedUsersResponse}
        onInviteUserClick={mockOnInviteUserClick}
      />,
      { wrapper },
    );

    const addUserButton = screen.getByText('actions.addUser');
    await fireEvent.click(addUserButton);

    expect(mockOnInviteUserClick).toHaveBeenCalled();
  });

  it('should handle filter changes internally', async () => {
    render(
      <InvitedUsersTab
        initialData={mockInvitedUsersResponse}
        onInviteUserClick={mockOnInviteUserClick}
      />,
      { wrapper },
    );

    const filterInput = screen.getByPlaceholderText('list.filter.placeholder');

    // The component should handle its own filter logic now
    await fireEvent.change(filterInput, { target: { value: 'test' } });

    // Verify the input value is updated (internal state management)
    await waitFor(() => {
      expect(filterInput).toHaveValue('test');
    });
  });

  it('should show action dropdown and handle cancel invitation', async () => {
    render(
      <InvitedUsersTab
        initialData={mockInvitedUsersResponse}
        onInviteUserClick={mockOnInviteUserClick}
      />,
      { wrapper },
    );

    const dropDowns = screen.getAllByLabelText('list.actions.label');
    expect(dropDowns.length).toBeGreaterThan(0);

    // Click the dropdown on the first user
    await fireEvent.click(dropDowns[0]);

    // Find and click the cancel button
    const cancelButton = screen.getByText('list.actions.cancel.label');
    await fireEvent.click(cancelButton);

    // Check that cancel confirmation modal appears
    await waitFor(() => {
      expect(
        screen.getByText('list.actions.cancel.confirmation.title'),
      ).toBeInTheDocument();
    });
  });

  it('should show action dropdown and handle resend invitation', async () => {
    render(
      <InvitedUsersTab
        initialData={mockInvitedUsersResponse}
        onInviteUserClick={mockOnInviteUserClick}
      />,
      { wrapper },
    );

    const dropDowns = screen.getAllByLabelText('list.actions.label');
    expect(dropDowns.length).toBeGreaterThan(0);

    // Click the dropdown on the first user
    await fireEvent.click(dropDowns[0]);

    // Find and click the resend button
    const resendButton = screen.getByText('list.actions.resend.label');
    await fireEvent.click(resendButton);

    // Check that resend confirmation modal appears
    await waitFor(() => {
      expect(
        screen.getByText('list.actions.resend.confirmation.title'),
      ).toBeInTheDocument();
    });
  });
});
