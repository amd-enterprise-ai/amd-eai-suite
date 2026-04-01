// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  convertCamelToSnakeParams,
  getErrorMessage,
} from '@amdenterpriseai/utils/app';
import { APIRequestError } from '@amdenterpriseai/utils/app';

import {
  ChipDisplayVariant,
  Dataset,
  DatasetType,
} from '@amdenterpriseai/types';

export const DATASET_FILESIZE_LIMIT = 100 * 1024 * 1024; // 100MB

export const getDatasetTypeVariants = (
  t: (key: string) => string,
): Record<DatasetType, ChipDisplayVariant> => ({
  [DatasetType.Finetuning]: {
    label: t(`types.${DatasetType.Finetuning}`),
    color: 'warning',
  },
  [DatasetType.Evaluation]: {
    label: t(`types.${DatasetType.Evaluation}`),
    color: 'secondary',
  },
});

export const getDatasets = async (
  projectId: string,
  params?: {
    type?: DatasetType;
    name?: string;
  },
) => {
  const queryParams = params ? convertCamelToSnakeParams(params) : '';

  const url = queryParams
    ? `/api/namespaces/${projectId}/datasets?${queryParams}`
    : `/api/namespaces/${projectId}/datasets`;

  const response = await fetch(url, {
    method: 'GET',
  });

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to list datasets: ${errorMessage}`,
      response.status,
    );
  }

  const json = await response.json();
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
  const response = await fetch(`/api/namespaces/${projectId}/datasets/${id}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get dataset: ${errorMessage}`,
      response.status,
    );
  }

  return await response.json();
};

export const deleteDatasets = async (ids: string[], projectId: string) => {
  const response = await fetch(`/api/namespaces/${projectId}/datasets/delete`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      ids: ids,
    }),
  });

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to delete datasets: ${errorMessage}`,
      response.status,
    );
  }

  return await response.json();
};

export const downloadDatasetById = async (id: string, projectId: string) => {
  const response = await fetch(
    `/api/namespaces/${projectId}/datasets/${id}/download`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    },
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to download dataset: ${errorMessage}`,
      response.status,
    );
  }
  const blob = await response.blob();

  const disposition = response.headers.get('Content-Disposition');
  let filename = `dataset-${id}.jsonl`;

  if (disposition) {
    const match = disposition.match(/filename="?([^"]+)"?/);
    if (match?.[1]) filename = match[1];
  }
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

  formData.append('name', name);
  formData.append('description', description);
  formData.append('jsonl', dataset);
  formData.append('type', type);

  const response = await fetch(`/api/namespaces/${projectId}/datasets/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to upload datasets: ${errorMessage}`,
      response.status,
    );
  }
  return await response.json();
};
