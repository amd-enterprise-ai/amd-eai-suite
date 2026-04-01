// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { deleteModel, deployModel, finetuneModel } from '@/lib/app/models';

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
      const mockResponse = { success: true };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await deleteModel(mockModelId, mockProjectId);

      expect(mockFetch).toHaveBeenCalledWith(
        `/api/namespaces/${mockProjectId}/models/${mockModelId}`,
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
        `/api/namespaces/${mockProjectId}/models/${mockModelId}`,
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
        `/api/namespaces/${mockProjectId}/models/${mockModelId}`,
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

    it('should return snake_case response as-is', async () => {
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

      expect(result).toEqual(mockResponse);
    });

    it('should handle empty response correctly', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(null),
      });

      const result = await deleteModel(mockModelId, mockProjectId);
      expect(result).toBeNull();
    });

    it('should handle response without JSON correctly', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(undefined),
      });

      const result = await deleteModel(mockModelId, mockProjectId);
      expect(result).toBeUndefined();
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
        `/api/namespaces/${mockProjectId}/models/${encodeURIComponent(specialModelId)}`,
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
        `/api/namespaces/${mockProjectId}/models/${longModelId}`,
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
        `/api/namespaces/${mockProjectId}/models/${mockModelId}/deploy`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({}),
        },
      );

      expect(result).toEqual(mockWorkloadResponse);
    });

    it('should return snake_case response as-is', async () => {
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

      expect(result).toEqual(mockResponse);
    });

    it('should include display_name query param when displayName is provided', async () => {
      const mockWorkloadResponse = {
        id: 'workload-789',
        display_name: 'My Custom Name',
        status: 'pending',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockWorkloadResponse),
      });

      const result = await deployModel(
        mockModelId,
        mockProjectId,
        'My Custom Name',
      );

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(
          `/api/namespaces/${mockProjectId}/models/${mockModelId}/deploy?`,
        ),
        expect.objectContaining({ method: 'POST' }),
      );

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('display_name=My+Custom+Name');
      expect(result).toEqual(mockWorkloadResponse);
    });

    it('should not include query params when displayName is omitted', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ id: 'workload-123' }),
      });

      await deployModel(mockModelId, mockProjectId);

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).not.toContain('?');
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
      expect((error as APIRequestError).message).toContain(
        'Failed to deploy model',
      );
    });
  });

  describe('finetuneModel', () => {
    it('should successfully finetune a model without hf_token_secret_name', async () => {
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
        `/api/namespaces/${mockProjectId}/models/${mockModelId}/finetune`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            name: mockParams.name,
            dataset_id: mockParams.datasetId,
            epochs: mockParams.epochs,
            learning_rate: mockParams.learningRate,
            batch_size: mockParams.batchSize,
          }),
        },
      );

      expect(result).toEqual({
        id: 'model-123',
        name: 'test-finetuned-model',
      });
    });

    it('should include hf_token_secret_name when provided', async () => {
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
        `/api/namespaces/${mockProjectId}/models/${mockModelId}/finetune`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            name: mockParams.name,
            dataset_id: mockParams.datasetId,
            epochs: mockParams.epochs,
            learning_rate: mockParams.learningRate,
            batch_size: mockParams.batchSize,
            hf_token_secret_name: mockParams.hfTokenSecretName,
          }),
        },
      );
    });

    it('should not include hf_token_secret_name when not provided', async () => {
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
      expect(requestBody).not.toHaveProperty('hf_token_secret_name');
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
