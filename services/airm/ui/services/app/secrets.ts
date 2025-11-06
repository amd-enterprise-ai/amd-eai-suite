// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { getErrorMessage } from '@/utils/app/api-helpers';
import { APIRequestError } from '@/utils/app/errors';

import {
  AssignSecretRequest,
  CreateSecretRequest,
  SecretsResponse,
} from '@/types/secrets';

export const fetchSecrets = async (): Promise<SecretsResponse> => {
  const response = await fetch('/api/secrets');

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to get secrets: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
  return response.json();
};

export const fetchProjectSecrets = async (projectId: string) => {
  if (!projectId) {
    throw new APIRequestError('Project ID is required', 400);
  }

  const response = await fetch(`/api/projects/${projectId}/secrets`);

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to get secrets: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
  return response.json();
};

export const fetchWorkbenchSecrets = async (projectId: string) => {
  const response = await fetch(`/api/workbench/secrets?projectId=${projectId}`);

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to get workbench secrets: ${await getErrorMessage(response)}`,
      response.status,
    );
  }

  return response.json();
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
    throw new APIRequestError(
      `Failed to unassign secret from project: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
};

export const createSecret = async (request: CreateSecretRequest) => {
  const response = await fetch('/api/secrets', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new APIRequestError(
      `Failed to create secret: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
  return response.json();
};

export const updateSecretAssignment = async (
  requestId: string,
  request: AssignSecretRequest,
) => {
  const response = await fetch(`/api/secrets/${requestId}/assign`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new APIRequestError(
      `Failed to update secret assignment: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
  return response.json();
};

export const assignSecretToProject = async (
  projectId: string,
  secretId: string,
) => {
  const response = await fetch(
    `/api/projects/${projectId}/secrets/${secretId}/assign`,
    {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
    },
  );
  if (!response.ok) {
    throw new APIRequestError(
      `Failed to assign secret to project: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
  return response.json();
};

export const deleteSecret = async (secretId: string) => {
  const response = await fetch(`/api/secrets/${secretId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new APIRequestError(
      `Failed to delete secret: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
};
