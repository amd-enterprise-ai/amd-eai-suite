// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  convertCamelToSnakeParams,
  getErrorMessage,
} from '@/utils/app/api-helpers';
import { APIRequestError } from '@/utils/app/errors';

import { Dataset, DatasetType } from '@/types/datasets';

export const getDatasets = async (
  projectId: string,
  params?: {
    type?: DatasetType;
    name?: string;
  },
) => {
  const queryParams = convertCamelToSnakeParams({
    ...params,
    projectId,
  });

  const response = await fetch(`/api/datasets?${queryParams}`, {
    method: 'GET',
  });

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to list datasets: ${await getErrorMessage(response)}`,
      response.status,
    );
  }

  const json = await response.json();
  // Extract data from wrapped response
  return json.data;
};

/**
 * Retrieves a single dataset by ID.
 *
 * @param {string} id - The dataset ID
 * @param {string} projectId - The active project ID
 * @returns {Promise<Dataset>} A promise that resolves to a Dataset object.
 * @throws {APIRequestError} If the API request fails.
 */
export const getDataset = async (
  id: string,
  projectId: string,
): Promise<Dataset> => {
  const queryParams = convertCamelToSnakeParams({
    projectId,
  });

  const response = await fetch(`/api/datasets/${id}?${queryParams}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to get dataset: ${await getErrorMessage(response)}`,
      response.status,
    );
  }

  return await response.json();
};

export const deleteDatasets = async (ids: string[], projectId: string) => {
  const queryParams = convertCamelToSnakeParams({
    projectId,
  });

  const response = await fetch(`/api/datasets/delete?${queryParams}`, {
    method: 'POST',
    body: JSON.stringify({
      ids: ids,
    }),
  });

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to delete datasets: ${await getErrorMessage(response)}`,
      response.status,
    );
  }

  const json = await response.json();
  // batch_delete_datasets returns unwrapped list of deleted IDs
  return json;
};

export const downloadDatasetById = async (id: string, projectId: string) => {
  const queryParams = convertCamelToSnakeParams({
    projectId,
  });

  const response = await fetch(`/api/datasets/${id}/download?${queryParams}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) {
    throw new Error(
      `Failed to delete datasets: ${await getErrorMessage(response)}`,
    );
  }
  const blob = await response.blob();

  const disposition = response.headers.get('Content-Disposition');
  let filename = `dataset-${id}.jsonl`;

  if (disposition) {
    const match = disposition.match(/filename="?([^"]+)"?/);
    if (match?.[1]) filename = match[1];
  }
  // Download blob as a file
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
};

export const uploadDataset = async (
  name: string,
  description: string,
  type: DatasetType,
  dataset: File,
  projectId: string,
) => {
  const formData = new FormData();
  const queryParams = convertCamelToSnakeParams({
    projectId,
  });

  formData.append('name', name);
  formData.append('description', description);
  formData.append('file', dataset);
  formData.append('type', type);

  const response = await fetch(`/api/datasets?${queryParams}`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to upload datasets: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
  const json = await response.json();
  // uploadDataset returns unwrapped DatasetResponse
  return json;
};
