// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  assignRoleToUser,
  deleteUser,
  fetchInvitedUsers,
  fetchUser,
  fetchUsers,
  inviteUser,
  resendInvitation,
  updateUser,
} from '@/services/app/users';

import { APIRequestError } from '@/utils/app/errors';

import { UserRole } from '@/types/enums/user-roles';

vi.mock('@/utils/app/api-helpers', () => ({
  getErrorMessage: vi.fn().mockResolvedValue('error message'),
}));

const mockFetch = vi.fn();
globalThis.fetch = mockFetch as any;

describe('users service', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchUsers', () => {
    it('returns users on success', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: vi.fn().mockResolvedValue({ data: [{ id: '1' }] }),
      });
      const users = await fetchUsers();
      expect(users).toEqual({ data: [{ id: '1' }] });
      expect(mockFetch).toHaveBeenCalledWith('/api/users');
    });

    it('throws error on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false });
      await expect(fetchUsers()).rejects.toThrow(/^Failed to get users/);
    });
  });

  describe('fetchUser', () => {
    it('returns user on success', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: vi.fn().mockResolvedValue({ id: '1' }),
      });
      const user = await fetchUser('1');
      expect(user).toEqual({ id: '1' });
      expect(mockFetch).toHaveBeenCalledWith('/api/users/1');
    });

    it('throws error on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false });
      await expect(fetchUser('1')).rejects.toThrow(/^Failed to get user/);
    });
  });

  describe('fetchInvitedUsers', () => {
    it('returns invited users on success', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: vi.fn().mockResolvedValue({ data: [{ id: '2' }] }),
      });
      const users = await fetchInvitedUsers();
      expect(users).toEqual({ data: [{ id: '2' }] });
      expect(mockFetch).toHaveBeenCalledWith('/api/invited-users');
    });

    it('throws error on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false });
      await expect(fetchInvitedUsers()).rejects.toThrow(
        /^Failed to get invited users/,
      );
    });
  });

  describe('inviteUser', () => {
    const inviteUserData = {
      email: 'test@example.com',
      role: UserRole.PLATFORM_ADMIN,
    };

    it('returns invited user on success', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: vi.fn().mockResolvedValue({ id: '3' }),
      });
      const user = await inviteUser(inviteUserData as any);
      expect(user).toEqual({ id: '3' });
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/users',
        expect.objectContaining({
          method: 'POST',
        }),
      );
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 400 });
      await expect(inviteUser(inviteUserData as any)).rejects.toThrow(
        APIRequestError,
      );
    });
  });

  describe('deleteUser', () => {
    it('calls fetch with DELETE method', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });
      await deleteUser('1');
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/users/1',
        expect.objectContaining({
          method: 'DELETE',
        }),
      );
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 404 });
      await expect(deleteUser('1')).rejects.toThrow(APIRequestError);
    });
  });

  describe('resendInvitation', () => {
    it('calls fetch with POST method', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });
      await resendInvitation('2');
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/invited-users/2/resend-invitation',
        expect.objectContaining({
          method: 'POST',
        }),
      );
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 400 });
      await expect(resendInvitation('2')).rejects.toThrow(APIRequestError);
    });
  });

  describe('assignRoleToUser', () => {
    it('calls fetch with PUT method and correct body', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });
      const data = { userId: '1', role: UserRole.PLATFORM_ADMIN };
      const response = await assignRoleToUser(data);
      expect(response.ok).toBe(true);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/users/1/roles',
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify({ roles: [UserRole.PLATFORM_ADMIN] }),
        }),
      );
    });

    it('calls fetch with empty roles for TEAM_MEMBER', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });
      const data = { userId: '1', role: UserRole.TEAM_MEMBER };
      await assignRoleToUser(data);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/users/1/roles',
        expect.objectContaining({
          body: JSON.stringify({ roles: [] }),
        }),
      );
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 403 });
      await expect(
        assignRoleToUser({ userId: '1', role: UserRole.PLATFORM_ADMIN }),
      ).rejects.toThrow(APIRequestError);
    });
  });

  describe('updateUser', () => {
    const updateUserData = { id: '1', firstName: 'John', lastName: 'Doe' };

    it('calls fetch with PUT method and correct body', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });
      await updateUser(updateUserData as any);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/users/1',
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify({ first_name: 'John', last_name: 'Doe' }),
        }),
      );
    });

    it('throws APIRequestError on failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 400 });
      await expect(updateUser(updateUserData as any)).rejects.toThrow(
        APIRequestError,
      );
    });
  });
});
