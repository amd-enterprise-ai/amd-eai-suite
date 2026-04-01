// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  convertCamelToSnake,
  getErrorMessage,
} from '@amdenterpriseai/utils/app';
import { APIRequestError } from '@amdenterpriseai/utils/app';
import { ApiKeyDetails, ApiKeysResponse } from '@amdenterpriseai/types';

export const fetchProjectApiKeys = async (
  projectId: string,
): Promise<ApiKeysResponse> => {
  const response = await fetch(`/api/namespaces/${projectId}/api-keys`);

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch API keys: ${errorMessage}`,
      response.status,
    );
  }

  return response.json();
};

export const deleteApiKey = async (projectId: string, apiKeyId: string) => {
  const response = await fetch(
    `/api/namespaces/${projectId}/api-keys/${apiKeyId}`,
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
  data: { name: string; ttl?: string; aimIds?: string[] },
) => {
  const response = await fetch(`/api/namespaces/${projectId}/api-keys`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(convertCamelToSnake(data)),
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
    `/api/namespaces/${projectId}/api-keys/${apiKeyId}`,
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

export const updateApiKeyBindings = async (
  projectId: string,
  apiKeyId: string,
  aimIds: string[],
) => {
  const response = await fetch(
    `/api/namespaces/${projectId}/api-keys/${apiKeyId}`,
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(convertCamelToSnake({ aimIds })),
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
