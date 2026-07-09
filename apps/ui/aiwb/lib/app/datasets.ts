// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getErrorMessage } from '@amdenterpriseai/utils/app';
import { APIRequestError } from '@amdenterpriseai/utils/app';

import { ChipDisplayVariant } from '@amdenterpriseai/types';
import { Dataset, DatasetType } from '@/types/datasets';
import { PaginatedList } from '@/types/pagination';

import { fetchAllPages } from './pagination';

export const DATASET_FILESIZE_LIMIT = 100 * 1024 * 1024; // 100MB

export const getDatasetTypeVariants = (
  t: (key: string) => string,
): Record<DatasetType, ChipDisplayVariant> => ({
  [DatasetType.Finetuning]: {
    label: t(`types.${DatasetType.Finetuning}`),
    color: 'warning',
  },
});

export interface ListDatasetsOptions {
  type?: DatasetType;
  name?: string;
}

// TODO(EAI-6599): Replace getAllDatasets callers (e.g. FinetuneDrawer) with a
// server-side picker so the UI scales to projects with >100 datasets without
// walking every page.

const buildDatasetsListUrl = (
  projectId: string,
  page: number,
  pageSize: number,
  options: ListDatasetsOptions,
) => {
  const params = new URLSearchParams();
  params.append('pageSize', String(pageSize));
  params.append('page', String(page));
  if (options.type) {
    params.append('type', options.type);
  }
  if (options.name) {
    params.append('name', options.name);
  }
  return `/api/projects/${projectId}/datasets?${params}`;
};

/**
 * Fetches a single page of datasets for a project.
 *
 * Backed by GET /v1/projects/{project}/datasets. Returns the raw paginated
 * envelope so callers can drive UI pagination. The `type` filter is a single
 * exact match (backend does not support repeated values), and `name` matches
 * a single exact dataset name.
 *
 * @param {string} projectId - The project (1:1 with namespace) to list in.
 * @param {object} [options] - Optional filters and pagination controls.
 * @returns {Promise<PaginatedList<Dataset>>} The requested page and pagination metadata.
 * @throws {APIRequestError} If the API request fails.
 */
export const listDatasets = async (
  projectId: string,
  options: ListDatasetsOptions & {
    page?: number;
    pageSize?: number;
  } = {},
): Promise<PaginatedList<Dataset>> => {
  const { page = 1, pageSize = 10, ...filters } = options;
  const response = await fetch(
    buildDatasetsListUrl(projectId, page, pageSize, filters),
    {
      method: 'GET',
    },
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to list datasets: ${errorMessage}`,
      response.status,
    );
  }

  return await response.json();
};

/**
 * Lists every dataset for a project by walking all pages.
 *
 * Thin wrapper around fetchAllPages — see `apps/ui/aiwb/AGENTS.md`
 * "Paginated list loaders". Intended for callers that need an exhaustive
 * list (e.g., populating a fine-tuning dataset dropdown).
 *
 * @param {string} projectId - The project (1:1 with namespace) to list in.
 * @param {ListDatasetsOptions} [options] - Optional type and name filters.
 * @returns {Promise<Dataset[]>} All datasets matching the filters.
 * @throws {APIRequestError} If any underlying page request fails.
 */
export const getAllDatasets = (
  projectId: string,
  options: ListDatasetsOptions = {},
): Promise<Dataset[]> =>
  fetchAllPages<Dataset>((page, pageSize) =>
    listDatasets(projectId, { ...options, page, pageSize }),
  );

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
  const response = await fetch(`/api/projects/${projectId}/datasets/${id}`, {
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

export const deleteDataset = async (
  id: string,
  projectId: string,
): Promise<void> => {
  const response = await fetch(`/api/projects/${projectId}/datasets/${id}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to delete dataset ${id}: ${errorMessage}`,
      response.status,
    );
  }
};

export interface DeleteDatasetsResult {
  succeededIds: string[];
  failed: Array<{ id: string; error: APIRequestError | Error }>;
}

export const deleteDatasets = async (
  ids: string[],
  projectId: string,
): Promise<DeleteDatasetsResult> => {
  const results = await Promise.allSettled(
    ids.map((id) => deleteDataset(id, projectId)),
  );
  const succeededIds: string[] = [];
  const failed: DeleteDatasetsResult['failed'] = [];
  results.forEach((result, idx) => {
    const id = ids[idx];
    if (result.status === 'fulfilled') {
      succeededIds.push(id);
    } else {
      failed.push({ id, error: result.reason });
    }
  });
  return { succeededIds, failed };
};

export const downloadDatasetById = async (id: string, projectId: string) => {
  const response = await fetch(
    `/api/projects/${projectId}/datasets/${id}/download`,
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

  const response = await fetch(`/api/projects/${projectId}/datasets`, {
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
