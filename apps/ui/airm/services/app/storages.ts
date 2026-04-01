// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getErrorMessage } from '@amdenterpriseai/utils/app';
import { APIRequestError } from '@amdenterpriseai/utils/app';

import {
  AssignStorageRequest,
  CreateStorageRequest,
} from '@amdenterpriseai/types';

export const fetchStorages = async () => {
  const response = await fetch('/api/storages');

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get storages: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const fetchProjectStorages = async (projectId: string) => {
  const response = await fetch(`/api/projects/${projectId}/storages`);

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get storages: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const deleteProjectStorage = async (
  projectId: string,
  storageId: string,
) => {
  const response = await fetch(
    `/api/projects/${projectId}/storages/${storageId}`,
    {
      method: 'DELETE',
    },
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to delete storage from project: ${errorMessage}`,
      response.status,
    );
  }
};

export const createStorage = async (request: CreateStorageRequest) => {
  const response = await fetch('/api/storages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to create storage: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const updateStorageAssignment = async (
  requestId: string,
  request: AssignStorageRequest,
) => {
  const response = await fetch(`/api/storages/${requestId}/assign`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to update storage assignment: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const assignStorageToProject = async (
  projectId: string,
  storageId: string,
) => {
  const response = await fetch(
    `/api/projects/${projectId}/storages/${storageId}`,
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
      `Failed to assign storage to project: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const deleteStorage = async (storageId: string) => {
  const response = await fetch(`/api/storages/${storageId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to delete storage: ${errorMessage}`,
      response.status,
    );
  }
};
