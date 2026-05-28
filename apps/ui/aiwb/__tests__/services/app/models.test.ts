// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { deleteModel, finetuneModel } from '@/lib/app/models';

import { APIRequestError } from '@amdenterpriseai/utils/app';
import { getStorageItem } from '@amdenterpriseai/utils/app';

import { beforeEach, describe, expect, it, vi } from 'vitest';

// Mock the storage utility
vi.mock('@amdenterpriseai/utils/app', async (importOriginal) => ({
  ...(await importOriginal()),
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
      mockFetch.mockResolvedValueOnce({ ok: true });

      const result = await deleteModel(mockModelId, mockProjectId);

      expect(mockFetch).toHaveBeenCalledWith(
        `/api/namespaces/${mockProjectId}/aims/models/${mockModelId}`,
        {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
          },
        },
      );
      // 204 No Content — deleteModel returns void
      expect(result).toBeUndefined();
    });

    it('should delete a model successfully', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });

      const result = await deleteModel(mockModelId, mockProjectId);

      expect(mockFetch).toHaveBeenCalledWith(
        `/api/namespaces/${mockProjectId}/aims/models/${mockModelId}`,
        {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
          },
        },
      );
      expect(result).toBeUndefined();
    });

    it('should handle undefined project ID gracefully', async () => {
      (getStorageItem as any).mockReturnValue(undefined);
      mockFetch.mockResolvedValueOnce({ ok: true });

      await deleteModel(mockModelId, mockProjectId);

      expect(mockFetch).toHaveBeenCalledWith(
        `/api/namespaces/${mockProjectId}/aims/models/${mockModelId}`,
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

    it('should return void regardless of response body', async () => {
      // deleteModel returns void (204 No Content) — response body is not parsed
      mockFetch.mockResolvedValueOnce({ ok: true });

      const result = await deleteModel(mockModelId, mockProjectId);

      expect(result).toBeUndefined();
    });

    it('should handle empty response correctly', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });

      const result = await deleteModel(mockModelId, mockProjectId);
      expect(result).toBeUndefined();
    });

    it('should handle response without JSON correctly', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });

      const result = await deleteModel(mockModelId, mockProjectId);
      expect(result).toBeUndefined();
    });
  });

  describe('Error handling and edge cases', () => {
    it('should handle malformed JSON response', async () => {
      // deleteModel does not parse the response body, so a broken json() has no effect
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.reject(new Error('Invalid JSON')),
      });

      const result = await deleteModel(mockModelId, mockProjectId);
      expect(result).toBeUndefined();
    });

    it('should handle special characters in model ID', async () => {
      const specialModelId = 'model-with-special-chars-!@#$%';
      mockFetch.mockResolvedValueOnce({ ok: true });

      await deleteModel(specialModelId, mockProjectId);

      expect(mockFetch).toHaveBeenCalledWith(
        `/api/namespaces/${mockProjectId}/aims/models/${encodeURIComponent(specialModelId)}`,
        expect.objectContaining({
          method: 'DELETE',
        }),
      );
    });

    it('should handle very long model ID', async () => {
      const longModelId = 'a'.repeat(1000);
      mockFetch.mockResolvedValueOnce({ ok: true });

      await deleteModel(longModelId, mockProjectId);

      expect(mockFetch).toHaveBeenCalledWith(
        `/api/namespaces/${mockProjectId}/aims/models/${longModelId}`,
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

  describe('finetuneModel', () => {
    it('should successfully finetune a model without hfTokenSecretName', async () => {
      const mockParams = {
        name: 'test-finetuned-model',
        datasetId: 'dataset-123',
        epochs: 10,
        learningRate: 0.001,
        batchSize: 8,
      };

      const mockResponse = {
        id: 'model-123',
        name: 'test-finetuned-model',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await finetuneModel(
        mockModelId,
        mockParams,
        mockProjectId,
      );

      expect(mockFetch).toHaveBeenCalledWith(
        `/api/namespaces/${mockProjectId}/models/${mockModelId}/finetune?displayName=${encodeURIComponent(mockParams.name)}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            name: mockParams.name,
            datasetId: mockParams.datasetId,
            epochs: mockParams.epochs,
            learningRate: mockParams.learningRate,
            batchSize: mockParams.batchSize,
          }),
        },
      );

      expect(result).toEqual({
        id: 'model-123',
        name: 'test-finetuned-model',
      });
    });

    it('should include hfTokenSecretName when provided', async () => {
      const mockParams = {
        name: 'test-finetuned-model',
        datasetId: 'dataset-123',
        epochs: 10,
        learningRate: 0.001,
        batchSize: 8,
        hfTokenSecretName: 'hf-token-secret',
      };

      const mockResponse = {
        id: 'model-123',
        name: 'test-finetuned-model',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      await finetuneModel(mockModelId, mockParams, mockProjectId);

      expect(mockFetch).toHaveBeenCalledWith(
        `/api/namespaces/${mockProjectId}/models/${mockModelId}/finetune?displayName=${encodeURIComponent(mockParams.name)}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            name: mockParams.name,
            datasetId: mockParams.datasetId,
            epochs: mockParams.epochs,
            learningRate: mockParams.learningRate,
            batchSize: mockParams.batchSize,
            hfTokenSecretName: mockParams.hfTokenSecretName,
          }),
        },
      );
    });

    it('should not include hfTokenSecretName when not provided', async () => {
      const mockParams = {
        name: 'test-finetuned-model',
        datasetId: 'dataset-123',
        epochs: 10,
        learningRate: 0.001,
        batchSize: 8,
      };

      const mockResponse = {
        id: 'model-123',
        name: 'test-finetuned-model',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      await finetuneModel(mockModelId, mockParams, mockProjectId);

      const requestBody = JSON.parse(mockFetch.mock.calls[0][1].body as string);
      expect(requestBody).not.toHaveProperty('hfTokenSecretName');
    });

    it('should throw APIRequestError when finetune fails', async () => {
      const mockParams = {
        name: 'test-finetuned-model',
        datasetId: 'dataset-123',
        epochs: 10,
        learningRate: 0.001,
        batchSize: 8,
      };

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        text: () => Promise.resolve('Invalid parameters'),
      });

      const error = await finetuneModel(
        mockModelId,
        mockParams,
        mockProjectId,
      ).catch((e) => e);

      expect(error).toBeInstanceOf(APIRequestError);
      expect((error as APIRequestError).message).toContain(
        'Failed to finetune model',
      );
    });
  });
});
