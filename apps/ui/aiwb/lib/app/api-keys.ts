// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { APIRequestError, getErrorMessage } from '@amdenterpriseai/utils/app';
import {
  ApiKey,
  ApiKeyDetails,
  ApiKeyMetrics,
  ApiKeysResponse,
} from '@/types/api-keys';
import { PaginatedList } from '@/types/pagination';

import { fetchAllPages } from './pagination';

const fetchApiKeysPage = async (
  projectId: string,
  page: number,
  pageSize: number,
): Promise<PaginatedList<ApiKey>> => {
  const response = await fetch(
    `/api/projects/${projectId}/api-keys?pageSize=${pageSize}&page=${page}`,
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch API keys: ${errorMessage}`,
      response.status,
    );
  }
  return await response.json();
};

export const fetchProjectApiKeys = async (
  projectId: string,
): Promise<ApiKeysResponse> => {
  // Walks every page via the shared fetchAllPages utility (bounded
  // concurrency, throttled). EAI-6598 tracks migrating ApiKeysTable to
  // ServerSideDataTable so this loader can be retired in favour of a
  // server-side paginated table.
  const data = await fetchAllPages<ApiKey>((page, pageSize) =>
    fetchApiKeysPage(projectId, page, pageSize),
  );
  return { data };
};

export const deleteApiKey = async (
  projectId: string,
  apiKeyId: string,
): Promise<void> => {
  const response = await fetch(
    `/api/projects/${projectId}/api-keys/${apiKeyId}`,
    {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    },
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to delete API key: ${errorMessage}`,
      response.status,
    );
  }
};

export const createApiKey = async (
  projectId: string,
  data: { displayName: string; ttl?: string; aimIds?: string[] },
) => {
  const response = await fetch(`/api/projects/${projectId}/api-keys`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to create API key: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const fetchApiKeyDetails = async (
  projectId: string,
  apiKeyId: string,
): Promise<ApiKeyDetails> => {
  const response = await fetch(
    `/api/projects/${projectId}/api-keys/${apiKeyId}`,
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch API key details: ${errorMessage}`,
      response.status,
    );
  }

  return response.json();
};

export const fetchApiKeyMetrics = async (
  projectId: string,
  apiKeyId: string,
  params?: { start?: string; end?: string },
): Promise<ApiKeyMetrics> => {
  const searchParams = new URLSearchParams();
  if (params?.start) searchParams.set('start', params.start);
  if (params?.end) searchParams.set('end', params.end);
  const query = searchParams.toString();

  const response = await fetch(
    `/api/projects/${projectId}/api-keys/${apiKeyId}/metrics${query ? `?${query}` : ''}`,
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch API key metrics: ${errorMessage}`,
      response.status,
    );
  }

  return response.json();
};

export const updateApiKeyBindings = async (
  projectId: string,
  apiKeyId: string,
  aimIds: string[],
): Promise<ApiKeyDetails> => {
  const response = await fetch(
    `/api/projects/${projectId}/api-keys/${apiKeyId}`,
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ aimIds }),
    },
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to update API key bindings: ${errorMessage}`,
      response.status,
    );
  }

  return response.json();
};
