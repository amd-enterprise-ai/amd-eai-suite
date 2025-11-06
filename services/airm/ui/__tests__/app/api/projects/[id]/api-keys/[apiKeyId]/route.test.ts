// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NextRequest } from 'next/server';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  GET,
  PATCH,
  DELETE,
} from '@/app/api/projects/[id]/api-keys/[apiKeyId]/route';

// Mock the route utilities
vi.mock('@/utils/server/route', () => ({
  authenticateRoute: vi.fn(),
  handleError: vi.fn(),
  proxyRequest: vi.fn(),
}));

import {
  authenticateRoute,
  handleError,
  proxyRequest,
} from '@/utils/server/route';

const mockAuthenticateRoute = vi.mocked(authenticateRoute);
const mockHandleError = vi.mocked(handleError);
const mockProxyRequest = vi.mocked(proxyRequest);

describe('API Key Route Handlers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuthenticateRoute.mockResolvedValue({
      accessToken: 'mock-access-token',
    } as any);
  });

  describe('GET /api/projects/[id]/api-keys/[apiKeyId]', () => {
    it('should fetch API key details successfully', async () => {
      const mockApiKeyDetails = {
        id: '08576854-a03e-4d64-b016-40080ae8fd05',
        name: 'Test API Key',
        truncatedKey: 'amd_aim_api_key_••••••••1234',
        projectId: '5bb49f19-7741-4012-b8aa-8645b5bf18dc',
        ttl: '24h',
        renewable: true,
        numUses: 0,
        groups: [],
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
        createdBy: 'test@example.com',
        updatedBy: 'test@example.com',
      };

      mockProxyRequest.mockResolvedValue(mockApiKeyDetails);

      const req = new NextRequest(
        'http://localhost:8000/api/projects/5bb49f19-7741-4012-b8aa-8645b5bf18dc/api-keys/08576854-a03e-4d64-b016-40080ae8fd05',
      );
      const params = Promise.resolve({
        id: '5bb49f19-7741-4012-b8aa-8645b5bf18dc',
        apiKeyId: '08576854-a03e-4d64-b016-40080ae8fd05',
      });

      const response = await GET(req, { params });
      const data = await response.json();

      expect(mockAuthenticateRoute).toHaveBeenCalled();
      expect(mockProxyRequest).toHaveBeenCalledWith(
        req,
        expect.stringContaining(
          '/v1/api-keys/08576854-a03e-4d64-b016-40080ae8fd05?project_id=5bb49f19-7741-4012-b8aa-8645b5bf18dc',
        ),
        'mock-access-token',
      );
      expect(data).toEqual(mockApiKeyDetails);
    });

    it('should handle errors when fetching API key details', async () => {
      const error = new Error('API key not found');
      mockProxyRequest.mockRejectedValue(error);
      mockHandleError.mockReturnValue(
        new Response(JSON.stringify({ error: 'API key not found' }), {
          status: 404,
        }) as any,
      );

      const req = new NextRequest(
        'http://localhost:8000/api/projects/project-1/api-keys/key-1',
      );
      const params = Promise.resolve({ id: 'project-1', apiKeyId: 'key-1' });

      const response = await GET(req, { params });

      expect(mockHandleError).toHaveBeenCalledWith(error);
      expect(response.status).toBe(404);
    });
  });

  describe('PATCH /api/projects/[id]/api-keys/[apiKeyId]', () => {
    it('should update API key bindings successfully', async () => {
      const mockUpdatedDetails = {
        id: '08576854-a03e-4d64-b016-40080ae8fd05',
        name: 'Test API Key',
        groups: ['group-1', 'group-2'],
      };

      mockProxyRequest.mockResolvedValue(mockUpdatedDetails);

      const req = new NextRequest(
        'http://localhost:8000/api/projects/5bb49f19-7741-4012-b8aa-8645b5bf18dc/api-keys/08576854-a03e-4d64-b016-40080ae8fd05',
        {
          method: 'PATCH',
          body: JSON.stringify({ aim_ids: ['aim-1', 'aim-2'] }),
        },
      );
      const params = Promise.resolve({
        id: '5bb49f19-7741-4012-b8aa-8645b5bf18dc',
        apiKeyId: '08576854-a03e-4d64-b016-40080ae8fd05',
      });

      const response = await PATCH(req, { params });
      const data = await response.json();

      expect(mockAuthenticateRoute).toHaveBeenCalled();
      expect(mockProxyRequest).toHaveBeenCalledWith(
        req,
        expect.stringContaining(
          '/v1/api-keys/08576854-a03e-4d64-b016-40080ae8fd05?project_id=5bb49f19-7741-4012-b8aa-8645b5bf18dc',
        ),
        'mock-access-token',
      );
      expect(data).toEqual(mockUpdatedDetails);
    });

    it('should handle errors when updating API key bindings', async () => {
      const error = new Error('Update failed');
      mockProxyRequest.mockRejectedValue(error);
      mockHandleError.mockReturnValue(
        new Response(JSON.stringify({ error: 'Update failed' }), {
          status: 500,
        }) as any,
      );

      const req = new NextRequest(
        'http://localhost:8000/api/projects/project-1/api-keys/key-1',
        {
          method: 'PATCH',
          body: JSON.stringify({ aim_ids: [] }),
        },
      );
      const params = Promise.resolve({ id: 'project-1', apiKeyId: 'key-1' });

      const response = await PATCH(req, { params });

      expect(mockHandleError).toHaveBeenCalledWith(error);
      expect(response.status).toBe(500);
    });
  });

  describe('DELETE /api/projects/[id]/api-keys/[apiKeyId]', () => {
    it('should delete API key successfully', async () => {
      mockProxyRequest.mockResolvedValue({ status: 204 });

      const req = new NextRequest(
        'http://localhost:8000/api/projects/5bb49f19-7741-4012-b8aa-8645b5bf18dc/api-keys/08576854-a03e-4d64-b016-40080ae8fd05',
        { method: 'DELETE' },
      );
      const params = Promise.resolve({
        id: '5bb49f19-7741-4012-b8aa-8645b5bf18dc',
        apiKeyId: '08576854-a03e-4d64-b016-40080ae8fd05',
      });

      const response = await DELETE(req, { params });
      const data = await response.json();

      expect(mockAuthenticateRoute).toHaveBeenCalled();
      expect(mockProxyRequest).toHaveBeenCalledWith(
        req,
        expect.stringContaining(
          '/v1/api-keys/08576854-a03e-4d64-b016-40080ae8fd05?project_id=5bb49f19-7741-4012-b8aa-8645b5bf18dc',
        ),
        'mock-access-token',
      );
      expect(data).toEqual({ status: 204 });
    });
  });
});
