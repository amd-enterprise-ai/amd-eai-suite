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

import router from 'next/router';

import { deleteUser as deleteUserAPI } from '@/services/app/users';

import { APIRequestError } from '@/utils/app/errors';

import { DeleteUser } from '@/components/features/user';

import wrapper from '@/__tests__/ProviderWrapper';
import { Mock } from 'vitest';

vi.mock('@/services/app/users', () => ({
  deleteUser: vi.fn(),
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

const mockSession = {
  error: null as any,
  expires: '2125-01-01T00:00:00',
  user: {
    id: 'test',
    email: 'testing@test.com',
    roles: [],
  },
};

describe('DeleteUser', () => {
  beforeEach(() => {
    toastSuccessMock.mockClear();
    toastErrorMock.mockClear();
  });
  const setup = async () => {
    return render(
      <SessionProvider session={mockSession}>
        <DeleteUser id="1" email="test@test.com" />
      </SessionProvider>,
      { wrapper },
    );
  };

  it('should render delete button', () => {
    setup();
    expect(
      screen.getByRole('button', { name: 'detail.delete.action.label' }),
    ).toBeInTheDocument();
  });

  it('should open confirmation modal on delete button click', () => {
    setup();
    fireEvent.click(
      screen.getByRole('button', { name: 'detail.delete.action.label' }),
    );
    expect(
      screen.getByText('detail.delete.confirmation.title'),
    ).toBeInTheDocument();
  });

  it('should call deleteUserAPI and handle success', async () => {
    (deleteUserAPI as Mock).mockResolvedValueOnce({});

    const mockRouterPush = vi.fn();
    vi.spyOn(router, 'push').mockImplementation(mockRouterPush);

    await act(setup);

    await fireEvent.click(
      screen.getByRole('button', { name: 'detail.delete.action.label' }),
    );
    await fireEvent.click(
      screen.getByRole('button', { name: 'actions.confirm.title' }),
    );

    await waitFor(() => {
      expect(deleteUserAPI).toHaveBeenCalledWith('1');
      expect(mockRouterPush).toHaveBeenCalledWith('/users');
      expect(toastSuccessMock).toHaveBeenCalledWith(
        'detail.delete.notification.success',
      );
    });
  });

  it('should handle error', async () => {
    const mockError = new APIRequestError('test error', 400);
    (deleteUserAPI as Mock).mockRejectedValueOnce(mockError);
    await act(setup);
    await fireEvent.click(
      screen.getByRole('button', { name: 'detail.delete.action.label' }),
    );
    await fireEvent.click(
      screen.getByRole('button', { name: 'actions.confirm.title' }),
    );

    await waitFor(() => {
      expect(deleteUserAPI).toHaveBeenCalledWith('1');
      expect(toastErrorMock).toHaveBeenCalledWith(
        'detail.delete.notification.error',
        mockError,
      );
    });
  });

  it('should disable the delete button if the user is the currently logged in user', async () => {
    await act(() => {
      return render(
        <SessionProvider session={mockSession}>
          <DeleteUser id="1" email={mockSession.user.email} />
        </SessionProvider>,

        { wrapper },
      );
    });
    const deleteButton = screen.getByRole('button', {
      name: 'detail.delete.action.label',
    }) as HTMLInputElement;
    expect(deleteButton.disabled).toBeTruthy();
  });
});
