// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest, NextResponse } from 'next/server';

import {
  addUserToProject,
  deleteUserFromProject,
  getProject,
  getProjects,
} from '@/services/server/projects';

import { convertSnakeToCamel, getErrorMessage } from '@/utils/app/api-helpers';
import { proxyRequest } from '@/utils/server/route';

vi.mock('@/utils/app/api-helpers', () => ({
  convertSnakeToCamel: vi.fn((data) => ({ ...data, camelized: true })),
  getErrorMessage: vi.fn(async () => 'error message'),
}));
vi.mock('@/utils/server/route', () => ({
  proxyRequest: vi.fn(),
}));

const OLD_ENV = process.env;

beforeEach(() => {
  vi.resetModules();
  process.env = { ...OLD_ENV, AIRM_API_SERVICE_URL: 'http://test-api' };
});

afterEach(() => {
  process.env = OLD_ENV;
  vi.restoreAllMocks();
});

describe('getProjects', () => {
  it('returns camelized projects on success', async () => {
    const mockJson = { projects: [{ id: 1 }], test: 'snake_case' };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(mockJson),
    } as any);

    const result = await getProjects('token');
    expect(global.fetch).toHaveBeenCalledWith(
      'http://test-api/v1/projects',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer token',
        }),
      }),
    );
    expect(convertSnakeToCamel).toHaveBeenCalledWith(mockJson);
    // Check for a property that exists on ProjectWithUserCount, e.g. 'id'
    expect(result.projects[0].id).toBe(1);
  });

  it('throws error on failure', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      json: vi.fn(),
    } as any);

    await expect(getProjects('token')).rejects.toThrow(
      'Failed to get projects: error message',
    );
    expect(getErrorMessage).toHaveBeenCalled();
  });
});

describe('getProject', () => {
  it('returns camelized project on success', async () => {
    const mockJson = { id: '123', name: 'Test Project' };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue(mockJson),
    } as any);

    const result = await getProject('123', 'token');
    expect(global.fetch).toHaveBeenCalledWith(
      'http://test-api/v1/projects/123',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer token',
        }),
      }),
    );
    expect(convertSnakeToCamel).toHaveBeenCalledWith(mockJson);
    expect(result.id).toBe('123');
  });

  it('throws error on failure', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      json: vi.fn(),
    } as any);

    await expect(getProject('123', 'token')).rejects.toThrow(
      'Failed to get project: error message',
    );
    expect(getErrorMessage).toHaveBeenCalled();
  });
});

describe('addUserToProject', () => {
  it('returns response on success', async () => {
    const mockResponse = { ok: true };
    global.fetch = vi.fn().mockResolvedValue(mockResponse as any);

    const result = await addUserToProject('u1', 'p1', 'token');
    expect(global.fetch).toHaveBeenCalledWith(
      'http://test-api/v1/projects/p1/users',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          Authorization: 'Bearer token',
        }),
        body: JSON.stringify({ user_ids: ['u1'] }),
      }),
    );
    expect(result).toBe(mockResponse);
  });

  it('throws error on failure', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      json: vi.fn(),
    } as any);

    await expect(addUserToProject('u1', 'p1', 'token')).rejects.toThrow(
      'Failed to add user to project: error message',
    );
    expect(getErrorMessage).toHaveBeenCalled();
  });
});

describe('deleteUserFromProject', () => {
  it('calls proxyRequest and returns 204 response', async () => {
    const mockRequest = {} as NextRequest;
    const mockProxy = proxyRequest as unknown as ReturnType<typeof vi.fn>;
    mockProxy.mockResolvedValue(undefined);

    const result = await deleteUserFromProject(
      'u1',
      'p1',
      mockRequest,
      'token',
    );
    expect(proxyRequest).toHaveBeenCalledWith(
      mockRequest,
      'http://test-api/v1/projects/p1/users/u1',
      'token',
    );
    expect(result).toBeInstanceOf(NextResponse);
    expect(result.status).toBe(204);
  });
});
