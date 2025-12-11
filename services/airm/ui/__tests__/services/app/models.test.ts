// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { deleteModel, deployModel } from '@/services/app/models';

import { APIRequestError } from '@/utils/app/errors';
import { getStorageItem } from '@/utils/app/storage';

import { beforeEach, describe, expect, it, vi } from 'vitest';

// Mock the storage utility
vi.mock('@/utils/app/storage', () => ({
  getStorageItem: vi.fn(),
}));

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Models Service - Delete Functionality', () => {
  const mockProjectId = 'test-project-id';
  const mockModelId = 'test-model-id';

  beforeEach(() => {
    vi.clearAllMocks();
    (getStorageItem as any).mockReturnValue(mockProjectId);
  });

  describe('deleteModel', () => {
    it('should successfully delete a model', async () => {
      const mockResponse = { success: true };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await deleteModel(mockModelId, mockProjectId);

      expect(mockFetch).toHaveBeenCalledWith(
        `/api/models/${mockModelId}?project_id=${mockProjectId}`,
        {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
          },
        },
      );
      expect(result).toEqual(mockResponse);
    });

    it('should delete a model successfully', async () => {
      const mockResponse = { success: true };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await deleteModel(mockModelId, mockProjectId);

      expect(mockFetch).toHaveBeenCalledWith(
        `/api/models/${mockModelId}?project_id=${mockProjectId}`,
        {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
          },
        },
      );
      expect(result).toEqual(mockResponse);
    });

    it('should handle undefined project ID gracefully', async () => {
      (getStorageItem as any).mockReturnValue(undefined);
      const mockResponse = { success: true };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      await deleteModel(mockModelId, mockProjectId);

      expect(mockFetch).toHaveBeenCalledWith(
        `/api/models/${mockModelId}?project_id=${mockProjectId}`,
        {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
          },
        },
      );
    });

    it('should throw APIRequestError when request fails with 404', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 404,
        text: () => Promise.resolve('Model not found'),
      });

      await expect(deleteModel(mockModelId, mockProjectId)).rejects.toThrow(
        APIRequestError,
      );
      await expect(deleteModel(mockModelId, mockProjectId)).rejects.toThrow(
        'Failed to delete model',
      );
    });

    it('should throw APIRequestError when request fails with 500', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: () => Promise.resolve('Internal server error'),
      });

      await expect(deleteModel(mockModelId, mockProjectId)).rejects.toThrow(
        APIRequestError,
      );
    });

    it('should throw APIRequestError when request fails with 403', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        text: () => Promise.resolve('Forbidden'),
      });

      const error = await deleteModel(mockModelId, mockProjectId).catch(
        (e) => e,
      );
      expect(error).toBeInstanceOf(APIRequestError);
      expect(error.statusCode).toBe(403);
    });

    it('should handle network errors correctly', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(deleteModel(mockModelId, mockProjectId)).rejects.toThrow(
        'Network error',
      );
    });

    it('should convert snake_case response to camelCase', async () => {
      const mockResponse = {
        delete_result: true,
        model_id: mockModelId,
        deleted_at: '2023-01-01T00:00:00Z',
      };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await deleteModel(mockModelId, mockProjectId);

      expect(result).toEqual({
        deleteResult: true,
        modelId: mockModelId,
        deletedAt: '2023-01-01T00:00:00Z',
      });
    });

    it('should handle empty response correctly', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(null),
      });

      const result = await deleteModel(mockModelId, mockProjectId);
      expect(result).toEqual({});
    });

    it('should handle response without JSON correctly', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(undefined),
      });

      const result = await deleteModel(mockModelId, mockProjectId);
      expect(result).toEqual({});
    });
  });

  describe('Error handling and edge cases', () => {
    it('should handle malformed JSON response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.reject(new Error('Invalid JSON')),
      });

      await expect(deleteModel(mockModelId, mockProjectId)).rejects.toThrow(
        'Invalid JSON',
      );
    });

    it('should handle special characters in model ID', async () => {
      const specialModelId = 'model-with-special-chars-!@#$%';
      const mockResponse = { success: true };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      await deleteModel(specialModelId, mockProjectId);

      expect(mockFetch).toHaveBeenCalledWith(
        `/api/models/${specialModelId}?project_id=${mockProjectId}`,
        expect.objectContaining({
          method: 'DELETE',
        }),
      );
    });

    it('should handle very long model ID', async () => {
      const longModelId = 'a'.repeat(1000);
      const mockResponse = { success: true };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      await deleteModel(longModelId, mockProjectId);

      expect(mockFetch).toHaveBeenCalledWith(
        `/api/models/${longModelId}?project_id=${mockProjectId}`,
        expect.objectContaining({
          method: 'DELETE',
        }),
      );
    });

    it('should handle timeout scenarios', async () => {
      // Simulate a timeout by rejecting after a delay
      mockFetch.mockImplementationOnce(() => {
        return new Promise((_, reject) => {
          setTimeout(() => reject(new Error('Request timeout')), 100);
        });
      });

      await expect(deleteModel(mockModelId, mockProjectId)).rejects.toThrow(
        'Request timeout',
      );
    });
  });

  describe('deployModel', () => {
    it('should successfully deploy a model and return workload directly', async () => {
      const mockWorkloadResponse = {
        id: 'workload-123',
        display_name: 'test-deployment',
        status: 'pending',
        type: 'inference',
        created_at: '2024-01-01T00:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockWorkloadResponse),
      });

      const result = await deployModel(mockModelId, mockProjectId);

      expect(mockFetch).toHaveBeenCalledWith(
        `/api/models/${mockModelId}/deploy?project_id=${mockProjectId}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({}),
        },
      );

      // Should return the workload object directly (not wrapped in .data)
      expect(result).toEqual({
        id: 'workload-123',
        displayName: 'test-deployment',
        status: 'pending',
        type: 'inference',
        createdAt: '2024-01-01T00:00:00Z',
      });
    });

    it('should convert snake_case response to camelCase', async () => {
      const mockResponse = {
        id: 'workload-456',
        display_name: 'my-model-deployment',
        project_id: mockProjectId,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await deployModel(mockModelId, mockProjectId);

      expect(result).toEqual({
        id: 'workload-456',
        displayName: 'my-model-deployment',
        projectId: mockProjectId,
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      });
    });

    it('should throw APIRequestError when model not found (404)', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: () => Promise.resolve('Model not found'),
      });

      const error = await deployModel(mockModelId, mockProjectId).catch(
        (e) => e,
      );
      expect(error).toBeInstanceOf(APIRequestError);
      expect(error.message).toContain('Failed to deploy model');
    });
  });
});
