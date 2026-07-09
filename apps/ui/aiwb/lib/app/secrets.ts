// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { SecretResponseData, CreateSecretRequest } from '@/types/secrets';
import { PaginatedList } from '@/types/pagination';
import { APIRequestError, getErrorMessage } from '@amdenterpriseai/utils/app';

import { fetchAllPages } from './pagination';

const fetchSecretsPage = async (
  projectId: string,
  page: number,
  pageSize: number,
  useCase?: string,
): Promise<PaginatedList<SecretResponseData>> => {
  const params = new URLSearchParams({
    pageSize: String(pageSize),
    page: String(page),
  });
  if (useCase) {
    params.set('useCase', useCase);
  }
  const response = await fetch(`/api/projects/${projectId}/secrets?${params}`);
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get project secrets: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const fetchProjectSecrets = async (
  projectId: string,
  useCase?: string,
): Promise<{ data: SecretResponseData[] }> => {
  if (!projectId) {
    throw new APIRequestError('Project ID is required', 400);
  }

  // Walks every page via the shared fetchAllPages utility (bounded
  // concurrency, throttled). A follow-up ticket will migrate the secrets
  // table to server-side pagination so this loader can be retired in
  // favour of a paginated table.
  const data = await fetchAllPages<SecretResponseData>((page, pageSize) =>
    fetchSecretsPage(projectId, page, pageSize, useCase),
  );
  return { data };
};

export const deleteProjectSecret = async (
  projectId: string,
  secretId: string,
) => {
  const response = await fetch(
    `/api/projects/${projectId}/secrets/${secretId}`,
    {
      method: 'DELETE',
    },
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to delete secret: ${errorMessage}`,
      response.status,
    );
  }
};

export const createProjectSecret = async (
  projectId: string,
  request: CreateSecretRequest,
): Promise<SecretResponseData> => {
  const response = await fetch(`/api/projects/${projectId}/secrets`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to create secret: ${errorMessage}`,
      response.status,
    );
  }

  return response.json();
};
