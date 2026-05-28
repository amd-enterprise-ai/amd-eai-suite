// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { APIRequestError, getErrorMessage } from '@amdenterpriseai/utils/app';

import {
  AIMModelResponse,
  FinetunableModel,
  Model,
  ModelFinetuneParams,
  ModelOnboardingStatus,
} from '@/types/models';

interface FinetuneModelRequest {
  name: string;
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
  return (json.data as FinetunableModel[]).map((model) => ({
    ...model,
    compatibleAccelerators: model.compatibleAccelerators ?? [],
    compatibleAcceleratorNames: model.compatibleAcceleratorNames ?? [],
  }));
};

/**
 * Fetches the raw list of namespace-scoped AIMModel CRs.
 * Returns the API response as-is (AIMModelResponse shape).
 * Callers are responsible for mapping items to their required shape.
 *
 * @param projectId - The namespace / project ID.
 * @param params - Optional filters (onboardingStatus, name).
 */
export const getModels = async (
  projectId: string,
  params?: {
    onboardingStatus?: ModelOnboardingStatus;
    name?: string;
  },
): Promise<AIMModelResponse[]> => {
  if (!projectId) {
    throw new APIRequestError('No project selected', 422);
  }

  const urlParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        urlParams.append(key, String(value));
      }
    });
  }
  const queryParams = urlParams.toString();

  const url = queryParams
    ? `/api/namespaces/${projectId}/aims/models?${queryParams}`
    : `/api/namespaces/${projectId}/aims/models`;

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

export const finetuneModel = async (
  id: string,
  params: ModelFinetuneParams,
  projectId: string,
) => {
  const body: FinetuneModelRequest = {
    name: params.name,
    datasetId: params.datasetId,
    epochs: params.epochs,
    learningRate: params.learningRate,
    batchSize: params.batchSize,
  };

  if (params.hfTokenSecretName) {
    body.hfTokenSecretName = params.hfTokenSecretName;
  }

  const bodyString = JSON.stringify(body);

  const response = await fetch(
    `/api/namespaces/${projectId}/models/${id}/finetune?displayName=${encodeURIComponent(params.name)}`,
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

  return await response.json();
};

export const deleteModel = async (
  name: string,
  projectId: string,
  force?: boolean,
) => {
  const baseUrl = `/api/namespaces/${projectId}/aims/models/${encodeURIComponent(name)}`;
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
