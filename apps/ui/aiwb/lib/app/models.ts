// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  APIRequestError,
  convertCamelToSnakeParams,
  convertSnakeToCamel,
  getErrorMessage,
} from '@amdenterpriseai/utils/app';

import {
  Model,
  ModelFinetuneParams,
  ModelOnboardingStatus,
} from '@amdenterpriseai/types';

interface FinetuneModelRequest {
  name: string;
  dataset_id: string;
  epochs: number;
  learning_rate: number;
  batch_size: number;
  hf_token_secret_name?: string;
}

/**
 * Retrieves a list of models that can be fine-tuned.
 *
 * @returns {Promise<string[]>} A promise that resolves to an array of canonical names of models that can be fine-tuned.
 * @throws {APIRequestError} If the API request fails.
 */
export const getFinetunableModels = async (): Promise<string[]> => {
  const url = `/api/finetunable`;

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
  return json.data;
};

export const getModels = async (
  projectId: string,
  params?: {
    onboardingStatus?: ModelOnboardingStatus;
    name?: string;
  },
): Promise<Model[]> => {
  if (!projectId) {
    throw new APIRequestError('No project selected', 422);
  }

  const queryParams = params ? convertCamelToSnakeParams(params) : '';

  const url = queryParams
    ? `/api/namespaces/${projectId}/models?${queryParams}`
    : `/api/namespaces/${projectId}/models`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get models: ${errorMessage}`,
      response.status,
    );
  }

  const json = await response.json();
  return json.data;
};

export const getModel = async (
  id: string,
  projectId: string,
): Promise<Model> => {
  if (!projectId) {
    throw new APIRequestError('No project selected', 422);
  }

  const response = await fetch(
    `/api/namespaces/${projectId}/models/${encodeURIComponent(id)}`,
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
      `Failed to get model: ${errorMessage}`,
      response.status,
    );
  }

  return await response.json();
};

export const finetuneModel = async (
  id: string,
  params: ModelFinetuneParams,
  projectId: string,
) => {
  const body: FinetuneModelRequest = {
    name: params.name,
    dataset_id: params.datasetId,
    epochs: params.epochs,
    learning_rate: params.learningRate,
    batch_size: params.batchSize,
  };

  if (params.hfTokenSecretName) {
    body.hf_token_secret_name = params.hfTokenSecretName;
  }

  const bodyString = JSON.stringify(body);

  const response = await fetch(
    `/api/namespaces/${projectId}/models/${id}/finetune`,
    {
      method: 'POST',
      body: bodyString,
      headers: {
        'Content-Type': 'application/json',
      },
    },
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to finetune model: ${errorMessage}`,
      response.status,
    );
  }

  const json = await response.json();
  const converted = convertSnakeToCamel(json);
  return converted;
};

export const deleteModel = async (id: string, projectId: string) => {
  const response = await fetch(
    `/api/namespaces/${projectId}/models/${encodeURIComponent(id)}`,
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
      `Failed to delete model: ${errorMessage}`,
      response.status,
    );
  }

  return await response.json();
};

export const deployModel = async (
  id: string,
  projectId: string,
  displayName?: string,
) => {
  const baseUrl = `/api/namespaces/${projectId}/models/${encodeURIComponent(id)}/deploy`;
  const queryParams = displayName
    ? convertCamelToSnakeParams({ displayName })
    : '';
  const url = queryParams ? `${baseUrl}?${queryParams}` : baseUrl;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({}),
  });

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to deploy model: ${errorMessage}`,
      response.status,
    );
  }

  return await response.json();
};
