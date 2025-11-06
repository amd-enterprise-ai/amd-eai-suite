// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { convertSnakeToCamel, getErrorMessage } from '@/utils/app/api-helpers';

import { ProjectSecretsResponse, SecretsResponse } from '@/types/secrets';

export const getSecrets = async (
  accessToken: string,
): Promise<SecretsResponse> => {
  const url = `${process.env.AIRM_API_SERVICE_URL}/v1/secrets`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (response.ok) {
    const json = await response.json();
    return convertSnakeToCamel(json);
  } else {
    throw new Error(
      `Failed to get secrets: ${await getErrorMessage(response)}`,
    );
  }
};

export const getProjectSecrets = async (
  accessToken: string,
  projectId: string,
): Promise<ProjectSecretsResponse> => {
  const url = `${process.env.AIRM_API_SERVICE_URL}/v1/projects/${projectId}/secrets`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (response.ok) {
    const json = await response.json();
    return convertSnakeToCamel(json);
  } else {
    throw new Error(
      `Failed to get project secrets: ${await getErrorMessage(response)}`,
    );
  }
};
