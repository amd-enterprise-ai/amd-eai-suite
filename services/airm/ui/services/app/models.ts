// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  convertCamelToSnakeParams,
  convertSnakeToCamel,
  getErrorMessage,
} from '@/utils/app/api-helpers';
import { APIRequestError } from '@/utils/app/errors';

import {
  Model,
  ModelFinetuneParams,
  ModelOnboardingStatus,
} from '@/types/models';

export interface ModelDownloadOptions {
  hfTokenSecretId?: string;
}

interface FinetuneModelRequest {
  name: string;
  dataset_id: string;
  epochs: number;
  learning_rate: number;
  batch_size: number;
  hf_token_secret_id?: string;
}

/**
 * Retrieves a list of models that can be fine-tuned.
 *
 * @param {string} projectId - The active project ID
 * @returns {Promise<{models: string[]}>} A promise that resolves to an object containing an array of canonical names of models that can be fine-tuned.
 * @throws {APIRequestError} If the API request fails.
 */
export const getFinetunableModels = async (
  projectId: string,
): Promise<{ models: string[] }> => {
  if (!projectId) {
    throw new APIRequestError(`No project selected`, 422);
  }

  const queryParams = convertCamelToSnakeParams({
    projectId,
  });

  const url = `/api/models/finetunable?${queryParams}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new APIRequestError(await getErrorMessage(response), response.status);
  }

  const json = await response.json();
  return convertSnakeToCamel(json);
};

/**
 * Retrieves a list of models with optional filtering parameters.
 *
 * @param {string} projectId - The active project ID
 * @param {Object} [params] - Optional parameters to filter the models.
 * @param {ModelOnboardingStatus} [params.onboardingStatus] - Filter by onboarding status.
 * @param {string} [params.name] - Filter by model name.
 * @returns {Promise<Model[]>} A promise that resolves to an array of Model objects.
 * @throws {APIRequestError} If the API request fails.
 */
export const getModels = async (
  projectId: string,
  params?: {
    onboardingStatus?: ModelOnboardingStatus;
    name?: string;
  },
): Promise<Model[]> => {
  if (!projectId) {
    throw new APIRequestError(`No project selected`, 422);
  }

  const queryParams = convertCamelToSnakeParams({
    ...params,
    projectId: projectId,
  });

  const url = `/api/models?${queryParams}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new APIRequestError(await getErrorMessage(response), response.status);
  }

  const json = await response.json();
  return convertSnakeToCamel(json);
};

/**
 * Initiates a fine-tuning job for a specific model.
 *
 * @param {string} id - The ID of the model to fine-tune.
 * @param {ModelFinetuneParams} params - Fine-tuning parameters.
 * @param {string} params.name - The name for the fine-tuned model.
 * @param {string} params.datasetId - Dataset ID used for fine-tuning.
 * @param {number} params.epochs - Number of training epochs.
 * @param {number} params.learningRate - Learning rate for training.
 * @param {number} params.batchSize - Batch size for training.
 * @param {string} params.hfTokenSecretId - Optional HuggingFace token secret ID.
 * @returns {Promise<any>} A promise that resolves to the fine-tuning job data.
 * @throws {APIRequestError} If the API request fails.
 */
export const finetuneModel = async (
  id: string,
  params: ModelFinetuneParams,
  projectId: string,
) => {
  const queryParams = convertCamelToSnakeParams({
    projectId: projectId,
  });

  const body: FinetuneModelRequest = {
    name: params.name,
    dataset_id: params.datasetId,
    epochs: params.epochs,
    learning_rate: params.learningRate,
    batch_size: params.batchSize,
  };

  if (params.hfTokenSecretId) {
    body.hf_token_secret_id = params.hfTokenSecretId;
  }

  const bodyString = JSON.stringify(body);

  const response = await fetch(`/api/models/${id}/finetune?${queryParams}`, {
    method: 'POST',
    body: bodyString,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to finetune model: ${await getErrorMessage(response)}`,
      response.status,
    );
  }

  const json = await response.json();
  return convertSnakeToCamel(json);
};

/**
 * Deletes a specific model by its ID.
 *
 * @param {string} id - The ID of the model to delete.
 * @returns {Promise<void>} A promise that resolves to the deletion result.
 * @throws {APIRequestError} If the API request fails.
 */
export const deleteModel = async (id: string, projectId: string) => {
  const queryParams = convertCamelToSnakeParams({
    projectId: projectId,
  });

  const response = await fetch(`/api/models/${id}?${queryParams}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to delete model: ${await getErrorMessage(response)}`,
      response.status,
    );
  }

  const json = await response.json();
  return convertSnakeToCamel(json);
};

/**
 * Downloads a model.
 *
 * @param {string} modelId - The Hugging face ID of the model to download.
 * @returns {Promise<any>} A promise that resolves to the download status.
 * @throws {APIRequestError} If the API request fails.
 */
export const downloadModel = async (
  modelId: string,
  projectId: string,
  options?: ModelDownloadOptions,
) => {
  const queryParams = convertCamelToSnakeParams({
    project_id: projectId,
    model_id: modelId,
  });

  const requestBody = options?.hfTokenSecretId
    ? {
        hf_token_secret_id: options.hfTokenSecretId,
      }
    : {};

  const response = await fetch(`/api/models/download?${queryParams}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to download model: ${await getErrorMessage(response)}`,
      response.status,
    );
  }

  const json = await response.json();
  return convertSnakeToCamel(json);
};

/**
 * Deploys a model to make it available for inference.
 *
 * @param {string} id - The ID of the model to deploy.
 * @returns {Promise<any>} A promise that resolves to the deployment result.
 * @throws {APIRequestError} If the API request fails.
 */
export const deployModel = async (id: string, projectId: string) => {
  const queryParams = convertCamelToSnakeParams({
    projectId: projectId,
  });

  const response = await fetch(`/api/models/${id}/deploy?${queryParams}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({}),
  });

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to deploy model: ${await getErrorMessage(response)}`,
      response.status,
    );
  }

  const json = await response.json();
  return convertSnakeToCamel(json);
};
