// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { getErrorMessage } from '@amdenterpriseai/utils/app';
import { APIRequestError } from '@amdenterpriseai/utils/app';

import {
  AssignSecretRequest,
  CreateProjectSecretRequest,
  CreateSecretRequest,
  SecretsResponse,
} from '@amdenterpriseai/types';

export const fetchSecrets = async (): Promise<SecretsResponse> => {
  const response = await fetch('/api/secrets');

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get secrets: ${errorMessage}`,
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
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get project secrets: ${errorMessage}`,
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
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to unassign secret from project: ${errorMessage}`,
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
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to create secret: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};
export const createProjectSecret = async (
  projectId: string,
  request: CreateProjectSecretRequest,
) => {
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
      `Failed to create project secret: ${errorMessage}`,
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
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to update secret assignment: ${errorMessage}`,
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
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to assign secret to project: ${errorMessage}`,
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
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to delete secret: ${errorMessage}`,
      response.status,
    );
  }
};
