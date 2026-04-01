// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  getErrorMessage,
  buildQueryParams,
  APIRequestError,
} from '@amdenterpriseai/utils/app';

import {
  CollectionRequestParams,
  MetricScalarResponse,
  WorkloadStatusStatsResponse,
  TimeSeriesResponse,
} from '@amdenterpriseai/types';
import {
  CreateProjectRequest,
  ProjectWithMembers,
  UpdateProjectRequest,
} from '@amdenterpriseai/types';

import {
  WorkloadWithMetricsServer,
  ProjectWorkloadsMetricsResponse,
} from '@/types/workloads';

export const fetchProject = async (
  project: string,
): Promise<ProjectWithMembers> => {
  const response = await fetch(`/api/projects/${project}`);
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get project: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const fetchSubmittableProjects = async () => {
  const response = await fetch(`/api/projects/submittable`);

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get submittable projects: ${errorMessage}`,
      response.status,
    );
  }

  return response.json();
};

export const fetchProjects = async () => {
  const response = await fetch('/api/projects');

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get projects: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const createProject = async (request: CreateProjectRequest) => {
  const response = await fetch('/api/projects', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to create project: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const updateProject = async (request: UpdateProjectRequest) => {
  // Only send description for updating - name is immutable
  const response = await fetch(`/api/projects/${request.id}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      description: request.description,
      quota: request.quota,
    }),
  });
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to update project: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const deleteProject = async (project: string) => {
  const response = await fetch(`/api/projects/${project}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to delete project: ${errorMessage}`,
      response.status,
    );
  }
};

export const getClusterProjects = async (clusterId: string) => {
  const response = await fetch(`/api/clusters/${clusterId}/projects`);
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get cluster projects: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const addUsersToProject = async (data: {
  userIds: string[];
  projectId: string;
}) => {
  const response = await fetch(`/api/projects/${data.projectId}/users`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ user_ids: data.userIds }),
  });
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to add user to project: ${errorMessage}`,
      response.status,
    );
  }
  return response;
};

export const deleteUserFromProject = async (data: {
  userId: string;
  projectId: string;
}) => {
  const response = await fetch(
    `/api/projects/${data.projectId}/users/${data.userId}`,
    {
      method: 'DELETE',
    },
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to delete user from project: ${errorMessage}`,
      response.status,
    );
  }
};

export const fetchProjectWorkloadsMetrics = async (
  projectId: string,
  collectionRequestParams: CollectionRequestParams<WorkloadWithMetricsServer>,
): Promise<ProjectWorkloadsMetricsResponse> => {
  const queryParams = buildQueryParams(
    collectionRequestParams.page,
    collectionRequestParams.pageSize,
    collectionRequestParams.filter,
    collectionRequestParams.sort,
  );

  const response = await fetch(
    `/api/projects/${projectId}/workloads/metrics?${queryParams}`,
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get Project Workloads Metrics: ${errorMessage}`,
      response.status,
    );
  }

  return response.json();
};

export const fetchProjectWorkloadsStatuses = async (
  projectId: string,
): Promise<WorkloadStatusStatsResponse> => {
  const response = await fetch(`/api/projects/${projectId}/workloads/stats`);

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get Project Workloads Statuses: ${errorMessage}`,
      response.status,
    );
  }

  return response.json();
};

export const fetchProjectGPUDeviceUtilization = async (
  projectId: string,
  start: Date,
  end: Date,
): Promise<TimeSeriesResponse> => {
  const response = await fetch(
    `/api/projects/${projectId}/metrics/gpu-device-utilization/?start=${start.toISOString()}&end=${end.toISOString()}`,
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get project GPU Device Utilization: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const fetchProjectGPUMemoryUtilization = async (
  projectId: string,
  start: Date,
  end: Date,
): Promise<TimeSeriesResponse> => {
  const response = await fetch(
    `/api/projects/${projectId}/metrics/gpu-memory-utilization/?start=${start.toISOString()}&end=${end.toISOString()}`,
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get project GPU Memory Utilization: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const fetchProjectAverageWaitTime = async (
  projectId: string,
  start: Date,
  end: Date,
): Promise<MetricScalarResponse> => {
  const response = await fetch(
    `/api/projects/${projectId}/metrics/average-wait-time/?start=${start.toISOString()}&end=${end.toISOString()}`,
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get project Average Wait Time: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const fetchProjectAverageGPUIdleTime = async (
  projectId: string,
  start: Date,
  end: Date,
): Promise<MetricScalarResponse> => {
  const response = await fetch(
    `/api/projects/${projectId}/metrics/average-gpu-idle-time/?start=${start.toISOString()}&end=${end.toISOString()}`,
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get project GPU Idle Time: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};
