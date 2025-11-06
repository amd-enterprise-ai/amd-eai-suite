// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getErrorMessage } from '@/utils/app/api-helpers';
import { APIRequestError } from '@/utils/app/errors';

import { AssignStorageRequest, CreateStorageRequest } from '@/types/storages';

export const fetchStorages = async () => {
  const response = await fetch('/api/storages');

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to get storages: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
  return response.json();
};

export const fetchProjectStorages = async (projectId: string) => {
  const response = await fetch(`/api/projects/${projectId}/storages`);

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to get storages: ${await getErrorMessage(response)}`,
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
    throw new APIRequestError(
      `Failed to delete storage from project: ${await getErrorMessage(response)}`,
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
    throw new APIRequestError(
      `Failed to create storage: ${await getErrorMessage(response)}`,
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
    throw new APIRequestError(
      `Failed to update storage assignment: ${await getErrorMessage(response)}`,
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
    throw new APIRequestError(
      `Failed to delete storage: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
};
