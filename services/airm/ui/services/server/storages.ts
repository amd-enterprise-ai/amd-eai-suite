// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { convertSnakeToCamel, getErrorMessage } from '@/utils/app/api-helpers';

import { ProjectStoragesResponse, StoragesResponse } from '@/types/storages';

export const getStorages = async (
  accessToken: string,
): Promise<StoragesResponse> => {
  const url = `${process.env.AIRM_API_SERVICE_URL}/v1/storages`;
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
      `Failed to get storages: ${await getErrorMessage(response)}`,
    );
  }
};

export const getProjectStorages = async (
  accessToken: string,
  projectId: string,
): Promise<ProjectStoragesResponse> => {
  const url = `${process.env.AIRM_API_SERVICE_URL}/v1/projects/${projectId}/storages`;
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
      `Failed to get project storages: ${await getErrorMessage(response)}`,
    );
  }
};
