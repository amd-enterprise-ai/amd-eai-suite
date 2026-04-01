// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  convertSnakeToCamel,
  getErrorMessage,
} from '@amdenterpriseai/utils/app';

import { Workload } from '@amdenterpriseai/types';
import { WorkloadsStats } from '@amdenterpriseai/types';
import { WorkloadStatusStatsResponse } from '@amdenterpriseai/types';

export const getWorkload = async (params: {
  accessToken: string;
  workloadId: string;
}): Promise<Workload> => {
  const { workloadId, accessToken } = params;
  const url = `${process.env.AIRM_API_SERVICE_URL}/v1/workloads/${workloadId}`;
  const response = await fetch(url, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    method: 'GET',
  });

  if (response.ok) {
    const json = await response.json();
    return convertSnakeToCamel(json);
  } else {
    throw new Error(`Failed to get workload`);
  }
};

export const getClusterWorkloadsStats = async (
  clusterId: string,
  accessToken: string,
): Promise<WorkloadStatusStatsResponse> => {
  const url = `${process.env.AIRM_API_SERVICE_URL}/v1/clusters/${clusterId}/workloads/stats`;
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
      `Failed to get cluster workload stats: ${await getErrorMessage(response)}`,
    );
  }
};

export const getWorkloadsStats = async (
  accessToken: string,
): Promise<WorkloadsStats> => {
  const url = `${process.env.AIRM_API_SERVICE_URL}/v1/workloads/stats`;
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
      `Failed to get workloads stats: ${await getErrorMessage(response)}`,
    );
  }
};
