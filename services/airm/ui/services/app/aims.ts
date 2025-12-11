// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  convertCamelToSnakeParams,
  convertCamelToSnake,
  convertSnakeToCamel,
  getErrorMessage,
} from '@/utils/app/api-helpers';
import { APIRequestError } from '@/utils/app/errors';
import { aimParser, aimsParser } from '@/utils/app/aims';

import { type Aim, type AimDeployPayload } from '@/types/aims';

export const getAims = async (projectId: string): Promise<Aim[]> => {
  if (!projectId) throw new APIRequestError(`No project selected`, 422);

  const queryParams = convertCamelToSnakeParams({
    projectId: projectId,
  });

  const url = `/api/aims?${queryParams}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to fetch AIM items: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
  const aims = await response.json();
  // Extract data from wrapped response
  const aimsData = aims.data;
  return aimsParser(aimsData);
};

export const getAimById = async (
  id: string,
  projectId: string,
): Promise<Aim> => {
  if (!projectId) throw new APIRequestError(`No project selected`, 422);

  const queryParams = convertCamelToSnakeParams({
    projectId: projectId,
  });

  const url = `/api/aims/${id}?${queryParams}`;

  const response = await fetch(url, {
    method: 'GET',
  });

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to fetch AIM item: ${await getErrorMessage(response)}`,
      response.status,
    );
  }

  const aim = await response.json();
  return { ...aim, ...aimParser(aim) };
};

/**
 * Deploys a model to make it available for inference.
 *
 * @param {string} id - The ID of the model to deploy.
 * @param {string} projectId - The ID of the project.
 * @param {AimDeployPayload} payload - The deployment configuration.
 * @returns {Promise<any>} A promise that resolves to the deployment result.
 * @throws {APIRequestError} If the API request fails.
 */
export const deployAim = async (
  id: string,
  projectId: string,
  payload?: AimDeployPayload,
) => {
  if (!projectId) throw new APIRequestError(`No project selected`, 422);

  const queryParams = convertCamelToSnakeParams({
    projectId: projectId,
  });

  const response = await fetch(`/api/aims/${id}/deploy?${queryParams}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(convertCamelToSnake(payload ?? {})),
  });

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to deploy AIM item: ${await getErrorMessage(response)}`,
      response.status,
    );
  }

  const json = await response.json();
  return convertSnakeToCamel(json);
};

/**
 * Undeploys an AIM to make it unavailable.
 *
 * @param {string} id - The ID of the AIM to undeploy.
 * @param {string} projectId - The ID of the project.
 * @returns {Promise<any>} A promise that resolves to the undeployment result.
 * @throws {APIRequestError} If the API request fails.
 */
export const undeployAim = async (id: string, projectId: string) => {
  if (!projectId) throw new APIRequestError(`No project selected`, 422);

  const queryParams = convertCamelToSnakeParams({
    projectId: projectId,
  });

  const response = await fetch(`/api/aims/${id}/undeploy?${queryParams}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to undeploy AIM item: ${await getErrorMessage(response)}`,
      response.status,
    );
  }

  const json = await response.json();
  return convertSnakeToCamel(json);
};
