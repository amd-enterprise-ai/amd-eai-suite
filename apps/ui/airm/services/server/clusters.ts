// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  convertSnakeToCamel,
  getErrorMessage,
} from '@amdenterpriseai/utils/app';

import {
  Cluster,
  ClusterNode,
  ClusterNodesResponse,
  ClusterStatsResponse,
  ClustersResponse,
} from '@amdenterpriseai/types';
import { WorkloadStatusStatsResponse } from '@amdenterpriseai/types';
import { ClusterProjectsResponse } from '@amdenterpriseai/types';

export const getClusters = async (
  accessToken: string,
): Promise<ClustersResponse> => {
  const url = `${process.env.AIRM_API_SERVICE_URL}/v1/clusters`;
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
      `Failed to get clusters: ${await getErrorMessage(response)}`,
    );
  }
};

export const getCluster = async (
  clusterId: string,
  accessToken: string,
): Promise<Cluster> => {
  const url = `${process.env.AIRM_API_SERVICE_URL}/v1/clusters/${clusterId}`;
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
      `Failed to get cluster: ${await getErrorMessage(response)}`,
    );
  }
};

export const getClusterNodes = async (
  clusterId: string,
  accessToken: string,
): Promise<ClusterNodesResponse> => {
  const url = `${process.env.AIRM_API_SERVICE_URL}/v1/clusters/${clusterId}/nodes`;
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
      `Failed to get cluster nodes: ${await getErrorMessage(response)}`,
    );
  }
};

export const getClusterNode = async (
  clusterId: string,
  nodeId: string,
  accessToken: string,
): Promise<ClusterNode> => {
  const url = `${process.env.AIRM_API_SERVICE_URL}/v1/clusters/${clusterId}/nodes/${nodeId}`;
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
      `Failed to get cluster node: ${await getErrorMessage(response)}`,
    );
  }
};

export const getClusterProjects = async (
  clusterId: string,
  accessToken: string,
): Promise<ClusterProjectsResponse> => {
  const url = `${process.env.AIRM_API_SERVICE_URL}/v1/clusters/${clusterId}/projects`;
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
      `Failed to get cluster quota: ${await getErrorMessage(response)}`,
    );
  }
};

export const getClusterStats = async (
  accessToken: string,
): Promise<ClusterStatsResponse> => {
  const url = `${process.env.AIRM_API_SERVICE_URL}/v1/clusters/stats`;
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
      `Failed to get cluster: ${await getErrorMessage(response)}`,
    );
  }
};

export const getClusterWorkloadsStatusStats = async (
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
      `Failed to get cluster workload status stats: ${await getErrorMessage(response)}`,
    );
  }
};
