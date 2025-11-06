// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import {
  deleteUser,
  getInvitedUsers,
  getUser,
  getUsers,
  inviteUser,
} from '@/services/server/users';

import { convertSnakeToCamel, getErrorMessage } from '@/utils/app/api-helpers';
import { proxyRequest } from '@/utils/server/route';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/utils/app/api-helpers', () => ({
  convertSnakeToCamel: vi.fn((x) => x),
  getErrorMessage: vi.fn(async () => 'error message'),
}));
vi.mock('@/utils/server/route', () => ({
  proxyRequest: vi.fn(),
}));

const OLD_ENV = process.env;

describe('users service', () => {
  beforeEach(() => {
    vi.resetModules();
    global.fetch = vi.fn();
    process.env = { ...OLD_ENV, AIRM_API_SERVICE_URL: 'http://test-api' };
  });

  afterEach(() => {
    vi.clearAllMocks();
    process.env = OLD_ENV;
  });

  describe('getUsers', () => {
    it('returns users on success', async () => {
      const mockJson = { users: [{ id: 1 }] };
      (global.fetch as any).mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(mockJson),
      });
      const result = await getUsers('token');
      expect(global.fetch).toHaveBeenCalledWith(
        'http://test-api/v1/users',
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer token',
          }),
        }),
      );
      expect(result).toEqual(mockJson);
      expect(convertSnakeToCamel).toHaveBeenCalledWith(mockJson);
    });

    it('throws error on failure', async () => {
      (global.fetch as any).mockResolvedValue({
        ok: false,
        json: vi.fn(),
      });
      await expect(getUsers('token')).rejects.toThrow(
        'Failed to get users: error message',
      );
      expect(getErrorMessage).toHaveBeenCalled();
    });
  });

  describe('getUser', () => {
    it('returns user on success', async () => {
      const mockJson = { id: 1 };
      (global.fetch as any).mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(mockJson),
      });
      const result = await getUser('1', 'token');
      expect(global.fetch).toHaveBeenCalledWith(
        'http://test-api/v1/users/1',
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer token',
          }),
        }),
      );
      expect(result).toEqual(mockJson);
      expect(convertSnakeToCamel).toHaveBeenCalledWith(mockJson);
    });

    it('throws error on failure', async () => {
      (global.fetch as any).mockResolvedValue({
        ok: false,
        json: vi.fn(),
      });
      await expect(getUser('1', 'token')).rejects.toThrow(
        'Failed to get user: error message',
      );
      expect(getErrorMessage).toHaveBeenCalled();
    });
  });

  describe('inviteUser', () => {
    it('calls proxyRequest and returns NextResponse.json', async () => {
      const mockRequest = {} as NextRequest;
      const mockJson = { id: '2' };
      (proxyRequest as any).mockResolvedValue(mockJson);
      const result = await inviteUser(mockRequest, 'token');
      expect(proxyRequest).toHaveBeenCalledWith(
        mockRequest,
        'http://test-api/v1/users',
        'token',
      );
      let responseBody;
      if (result instanceof NextResponse) {
        responseBody = await result.json();
      } else {
        responseBody = result;
      }
      expect(responseBody).toEqual(expect.objectContaining({ id: '2' }));
    });
  });

  describe('deleteUser', () => {
    it('calls proxyRequest and returns 204 response', async () => {
      const mockRequest = {} as NextRequest;
      (proxyRequest as any).mockResolvedValue(undefined);
      const result = await deleteUser('1', mockRequest, 'token');
      expect(proxyRequest).toHaveBeenCalledWith(
        mockRequest,
        'http://test-api/v1/users/1',
        'token',
      );
      expect(result).toBeInstanceOf(NextResponse);
      expect(result.status).toBe(204);
    });
  });

  describe('getInvitedUsers', () => {
    it('returns invited users on success', async () => {
      const mockJson = { invited: [{ id: 3 }] };
      (global.fetch as any).mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(mockJson),
      });
      const result = await getInvitedUsers('token');
      expect(global.fetch).toHaveBeenCalledWith(
        'http://test-api/v1/invited_users',
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer token',
          }),
        }),
      );
      expect(result).toEqual(mockJson);
      expect(convertSnakeToCamel).toHaveBeenCalledWith(mockJson);
    });

    it('throws error on failure', async () => {
      (global.fetch as any).mockResolvedValue({
        ok: false,
        json: vi.fn(),
      });
      await expect(getInvitedUsers('token')).rejects.toThrow(
        'Failed to get users: error message',
      );
      expect(getErrorMessage).toHaveBeenCalled();
    });
  });
});
