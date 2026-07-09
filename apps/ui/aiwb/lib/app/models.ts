// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { APIRequestError, getErrorMessage } from '@amdenterpriseai/utils/app';

import { FinetunableModel, ModelFinetuneParams } from '@/types/models';
import { AIMModel } from '@/types/aims';
import type { PaginatedList } from '@/types/pagination';

import { fetchAllPages } from './pagination';

interface FineTuningJobRequest {
  // baseModel is required by the new fine-tuning capability API (was a URL path
  // segment under the legacy endpoint).
  baseModel: string;
  displayName: string;
  datasetId: string;
  epochs?: number;
  learningRate?: number;
  batchSize?: number;
  hfTokenSecretName?: string;
}

/**
 * Retrieves a list of models that can be fine-tuned.
 *
 * @returns {Promise<FinetunableModel[]>} A promise that resolves to an array of finetunable model objects.
 * @throws {APIRequestError} If the API request fails.
 */
export const getFinetunableModels = async (): Promise<FinetunableModel[]> => {
  const url = `/api/fine-tuning/models`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get finetunable models: ${errorMessage}`,
      response.status,
    );
  }

  const json = await response.json();
  return (json.data as FinetunableModel[]).map((model) => ({
    ...model,
    compatibleAccelerators: model.compatibleAccelerators ?? [],
    compatibleAcceleratorNames: model.compatibleAcceleratorNames ?? [],
  }));
};

// EAI-6600 tracks replacing load-all UI consumers with server-side
// paginated tables; until then `listAllProjectFineTunedModels` walks
// every page via the shared fetchAllPages utility.

const buildFineTunedModelsListUrl = (
  projectId: string,
  page: number,
  pageSize: number,
) =>
  `/api/projects/${projectId}/fine-tuning/models?pageSize=${pageSize}&page=${page}`;

/**
 * Fetches a single page of fine-tuned models for a project.
 *
 * Backed by GET /v1/projects/{project}/fine-tuning/models. Returns the raw
 * paginated envelope so callers can drive UI pagination.
 *
 * @param {string} projectId - The project (1:1 with namespace) to list in.
 * @param {object} [options] - Optional pagination controls.
 * @returns {Promise<PaginatedList<AIMModel>>} The requested page and pagination metadata.
 * @throws {APIRequestError} If the API request fails.
 */
export const listProjectFineTunedModels = async (
  projectId: string,
  options: { page?: number; pageSize?: number } = {},
): Promise<PaginatedList<AIMModel>> => {
  if (!projectId) {
    throw new APIRequestError('No project selected', 422);
  }
  const { page = 1, pageSize = 10 } = options;
  const response = await fetch(
    buildFineTunedModelsListUrl(projectId, page, pageSize),
    {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    },
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get fine-tuned models: ${errorMessage}`,
      response.status,
    );
  }

  return await response.json();
};

/**
 * Lists every fine-tuned model in a project by walking all pages.
 *
 * Thin wrapper around fetchAllPages — see `apps/ui/aiwb/AGENTS.md`
 * "Paginated list loaders". Returns `[]` on any failure so callers
 * (joins against deployments / workloads) can render empty state
 * without an error boundary — matches `listAllInferenceDeployments`.
 *
 * Note: this is a philosophical shift from the previous `getProjectFineTunedModels`
 * stop-gap, which deliberately re-threw on failure to drive React Query error
 * states. Consumers that still need that behavior should switch to
 * `listProjectFineTunedModels` and handle the error themselves.
 *
 * @param {string} projectId - The project (1:1 with namespace) to list in.
 * @returns {Promise<AIMModel[]>} All fine-tuned models in the project.
 */
export const listAllProjectFineTunedModels = async (
  projectId: string,
): Promise<AIMModel[]> => {
  try {
    return await fetchAllPages<AIMModel>((page, pageSize) =>
      listProjectFineTunedModels(projectId, { page, pageSize }),
    );
  } catch (error) {
    console.warn('Error fetching fine-tuned models:', error);
    return [];
  }
};

export const finetuneModel = async (
  baseModelId: string,
  params: ModelFinetuneParams,
  projectId: string,
) => {
  const body: FineTuningJobRequest = {
    baseModel: baseModelId,
    displayName: params.displayName,
    datasetId: params.datasetId,
    epochs: params.epochs,
    learningRate: params.learningRate,
    batchSize: params.batchSize,
  };

  if (params.hfTokenSecretName) {
    body.hfTokenSecretName = params.hfTokenSecretName;
  }

  const bodyString = JSON.stringify(body);

  const response = await fetch(`/api/projects/${projectId}/fine-tuning/jobs`, {
    method: 'POST',
    body: bodyString,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to finetune model: ${errorMessage}`,
      response.status,
    );
  }

  return await response.json();
};

/**
 * Cancels an in-progress fine-tuning job.
 *
 * @param jobId - Workload UUID of the fine-tuning job.
 * @param projectId - The project / namespace.
 * @throws {APIRequestError} If the API request fails.
 */
export const cancelFineTuningJob = async (
  jobId: string,
  projectId: string,
): Promise<void> => {
  const response = await fetch(
    `/api/projects/${projectId}/fine-tuning/jobs/${encodeURIComponent(jobId)}`,
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
      `Failed to cancel fine-tuning job: ${errorMessage}`,
      response.status,
    );
  }
};

export const deleteModel = async (
  name: string,
  projectId: string,
  force?: boolean,
) => {
  const baseUrl = `/api/projects/${projectId}/fine-tuning/models/${encodeURIComponent(name)}`;
  const url = force ? `${baseUrl}?force=true` : baseUrl;

  const response = await fetch(url, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to delete model: ${errorMessage}`,
      response.status,
    );
  }
  // 204 No Content — no body to parse
};
