// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getErrorMessage } from '@/utils/app/api-helpers';
import { APIRequestError } from '@/utils/app/errors';

import {
  ClusterKubeConfig,
  ClusterStatsResponse,
  EditClusterRequest,
} from '@/types/clusters';

export const fetchClusters = async () => {
  const response = await fetch('/api/clusters');
  if (!response.ok) {
    throw new APIRequestError(
      `Failed to get clusters: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
  return response.json();
};

export const addCluster = async () => {
  const response = await fetch('/api/clusters', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: '{}',
  });
  if (!response.ok) {
    throw new APIRequestError(
      `Failed to create cluster: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
  return response.json();
};

export const getCluster = async (id: string) => {
  const response = await fetch(`/api/clusters/${id}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) {
    throw new APIRequestError(
      `Failed to fetching cluster: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
  return response.json();
};

export const deleteCluster = async (id: string) => {
  const response = await fetch(`/api/clusters/${id}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) {
    throw new APIRequestError(
      `Failed to delete cluster: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
  return response;
};

export const editCluster = async (id: string, data: EditClusterRequest) => {
  const response = await fetch(`/api/clusters/${id}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new APIRequestError(
      `Failed to edit cluster: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
  return response;
};

export const getClusterNodes = async (clusterId: string) => {
  const response = await fetch(`/api/clusters/${clusterId}/nodes`);
  if (!response.ok) {
    throw new APIRequestError(
      `Failed to get cluster nodes: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
  return response.json();
};

export const fetchClusterStatistics =
  async (): Promise<ClusterStatsResponse> => {
    const response = await fetch(`/api/clusters/stats`);
    if (!response.ok) {
      throw new Error(
        `Failed to get Cluster Statistics: ${await getErrorMessage(response)}`,
      );
    }
    return response.json();
  };

export const fetchClusterKubeConfig = async (
  clusterId: string,
): Promise<ClusterKubeConfig> => {
  const response = await fetch(`/api/clusters/${clusterId}/kube-config`);
  if (!response.ok) {
    throw new APIRequestError(
      `Failed to get cluster kube config: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
  return response.json();
};
