// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  getModelOnboardingStatus,
  onboardModel,
  previewModelSource,
} from '@/lib/app/model-import';
import type { ModelOnboardRequest } from '@/types/model-import';

const mockFetch = vi.fn();
global.fetch = mockFetch;

const onboardBody: ModelOnboardRequest = {
  repoId: 'meta-llama/Llama-3',
  revision: 'main',
  sha: 'abc123',
  displayName: 'My Model',
  description: 'A model',
  tags: ['llama'],
  image: 'amdenterpriseai/aim-base:0.11',
  hfTokenSecretName: 'hf-secret-1',
  customProfile: {
    imageFamilyId: 'aim-base',
    image: 'amdenterpriseai/aim-base:0.11',
    acceleratorType: 'gpu',
    acceleratorModel: '74a1',
    acceleratorCount: 1,
    precision: 'bf16',
  },
};

const okResponse = <T>(body: T) => ({
  ok: true,
  json: () => Promise.resolve(body),
});

const errorResponse = (status: number, body = 'upstream') => ({
  ok: false,
  status,
  text: () => Promise.resolve(body),
});

describe('model-import', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('previewModelSource', () => {
    it('rejects an empty project name without touching the network', async () => {
      await expect(
        previewModelSource('', { source: 'hf/model' }),
      ).rejects.toMatchObject({ statusCode: 422 });
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('rejects a blank model source without touching the network', async () => {
      await expect(
        previewModelSource('ns-1', { source: '   ' }),
      ).rejects.toMatchObject({ statusCode: 422 });
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('POSTs to the project-scoped preview BFF route with the full body', async () => {
      mockFetch.mockResolvedValueOnce(
        okResponse({
          repoId: 'a/b',
          revision: 'main',
          sha: 'sha-1',
          displayName: 'X',
          description: '',
          tags: [],
          gated: false,
          hfTokenRecommended: false,
          weightFiles: [],
        }),
      );

      const body = { source: 'a/b', hfTokenSecretName: 'project-hf-token' };
      await previewModelSource('my-project', body);

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit];
      expect(url).toBe('/api/projects/my-project/models/preview');
      expect(init.method).toBe('POST');
      expect(JSON.parse(init.body as string)).toEqual(body);
    });

    it('unwraps the ListResponse data envelope when present', async () => {
      const inner = {
        repoId: 'x/y',
        revision: 'main',
        sha: 'sha-1',
        displayName: 'Y',
        description: 'd',
        tags: ['t'],
        gated: true,
        hfTokenRecommended: true,
        weightFiles: [{ path: 'w.bin' }],
      };
      mockFetch.mockResolvedValueOnce(okResponse({ data: inner }));
      const result = await previewModelSource('ns', { source: 'x/y' });
      expect(result).toEqual(inner);
    });

    it('throws APIRequestError when the response is not ok', async () => {
      mockFetch.mockResolvedValueOnce(errorResponse(502));
      await expect(
        previewModelSource('ns', { source: 'x/y' }),
      ).rejects.toMatchObject({ statusCode: 502 });
    });
  });

  describe('onboardModel', () => {
    it('rejects an empty project name', async () => {
      await expect(onboardModel('', onboardBody)).rejects.toMatchObject({
        statusCode: 422,
      });
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('requires preview hub identifiers', async () => {
      await expect(
        onboardModel('ns', { ...onboardBody, sha: '' }),
      ).rejects.toMatchObject({ statusCode: 422 });
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('requires a container image ref', async () => {
      await expect(
        onboardModel('ns', { ...onboardBody, image: '' }),
      ).rejects.toMatchObject({ statusCode: 422 });
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('POSTs to the project-scoped onboard BFF route with the full body', async () => {
      mockFetch.mockResolvedValueOnce(okResponse({ status: 204 }));

      await onboardModel('my-project', onboardBody);

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit];
      expect(url).toBe('/api/projects/my-project/models/onboard');
      expect(init.method).toBe('POST');
      expect(JSON.parse(init.body as string)).toEqual(onboardBody);
    });

    it('accepts an upstream 204 No Content response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
        json: () => Promise.reject(new Error('no body')),
      });

      await expect(onboardModel('ns', onboardBody)).resolves.toBeUndefined();
    });

    it('throws APIRequestError when the response is not ok', async () => {
      mockFetch.mockResolvedValueOnce(errorResponse(500));
      await expect(onboardModel('ns', onboardBody)).rejects.toMatchObject({
        statusCode: 500,
      });
    });
  });

  describe('getModelOnboardingStatus', () => {
    it('rejects an empty project name', async () => {
      await expect(getModelOnboardingStatus('', 'id-1')).rejects.toMatchObject({
        statusCode: 422,
      });
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('rejects an empty model id', async () => {
      await expect(getModelOnboardingStatus('ns', '')).rejects.toMatchObject({
        statusCode: 422,
      });
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('GETs the project-scoped onboarding-status BFF route with encoded params', async () => {
      mockFetch.mockResolvedValueOnce(
        okResponse({ onboardingStatus: 'ready', percentComplete: 100 }),
      );

      await getModelOnboardingStatus('my project', 'mod/abc');

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit?];
      expect(url).toBe(
        '/api/projects/my%20project/models/mod%2Fabc/onboarding',
      );
      expect(init).toBeUndefined();
    });

    it('throws APIRequestError when the response is not ok', async () => {
      mockFetch.mockResolvedValueOnce(errorResponse(404));
      await expect(
        getModelOnboardingStatus('ns', 'missing'),
      ).rejects.toMatchObject({ statusCode: 404 });
    });
  });
});
