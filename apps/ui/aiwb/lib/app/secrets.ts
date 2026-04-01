// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { SecretResponseData, CreateSecretRequest } from '@/types/secrets';
import { APIRequestError, getErrorMessage } from '@amdenterpriseai/utils/app';

export const fetchProjectSecrets = async (
  namespace: string,
  useCase?: string,
): Promise<{ data: SecretResponseData[] }> => {
  if (!namespace) {
    throw new APIRequestError('Namespace is required', 400);
  }

  const params = useCase
    ? `?${new URLSearchParams({ use_case: useCase })}`
    : '';
  const response = await fetch(`/api/namespaces/${namespace}/secrets${params}`);

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get project secrets: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const deleteProjectSecret = async (
  namespace: string,
  secretId: string,
) => {
  const response = await fetch(
    `/api/namespaces/${namespace}/secrets/${secretId}`,
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
  namespace: string,
  request: CreateSecretRequest,
): Promise<SecretResponseData> => {
  const response = await fetch(`/api/namespaces/${namespace}/secrets`, {
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
