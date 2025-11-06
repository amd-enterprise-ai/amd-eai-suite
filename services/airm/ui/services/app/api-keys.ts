// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { convertCamelToSnake, getErrorMessage } from '@/utils/app/api-helpers';
import { APIRequestError } from '@/utils/app/errors';
import { ApiKeyDetails, ApiKeysResponse } from '@/types/api-keys';

export const fetchProjectApiKeys = async (
  projectId: string,
): Promise<ApiKeysResponse> => {
  const response = await fetch(`/api/projects/${projectId}/api-keys`);

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to fetch API keys: ${await getErrorMessage(response)}`,
      response.status,
    );
  }

  return response.json();
};

export const deleteApiKey = async (projectId: string, apiKeyId: string) => {
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
    throw new APIRequestError(
      `Failed to delete API key: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
};

export const createApiKey = async (
  projectId: string,
  data: { name: string; ttl?: string; aimIds?: string[] },
) => {
  const response = await fetch(`/api/projects/${projectId}/api-keys`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(convertCamelToSnake(data)),
  });
  if (!response.ok) {
    throw new APIRequestError(
      `Failed to create API key: ${await getErrorMessage(response)}`,
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
    throw new APIRequestError(
      `Failed to fetch API key details: ${await getErrorMessage(response)}`,
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
    `/api/projects/${projectId}/api-keys/${apiKeyId}`,
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(convertCamelToSnake({ aimIds })),
    },
  );

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to update API key bindings: ${await getErrorMessage(response)}`,
      response.status,
    );
  }

  return response.json();
};

export const bindApiKeyToGroup = async (
  projectId: string,
  apiKeyId: string,
  groupId: string,
) => {
  const response = await fetch(
    `/api/projects/${projectId}/api-keys/${apiKeyId}/bind-group`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(convertCamelToSnake({ groupId })),
    },
  );

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to bind API key to group: ${await getErrorMessage(response)}`,
      response.status,
    );
  }

  return response.json();
};

export const unbindApiKeyFromGroup = async (
  projectId: string,
  apiKeyId: string,
  groupId: string,
) => {
  const response = await fetch(
    `/api/projects/${projectId}/api-keys/${apiKeyId}/unbind-group`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(convertCamelToSnake({ groupId })),
    },
  );

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to unbind API key from group: ${await getErrorMessage(response)}`,
      response.status,
    );
  }

  return response.json();
};
