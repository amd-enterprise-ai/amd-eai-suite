// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getErrorMessage } from '@/utils/app/api-helpers';
import { APIRequestError } from '@/utils/app/errors';

import {
  Workload,
  WorkloadLogParams,
  WorkloadLogResponse,
} from '@/types/workloads';
import { WorkloadStatus, WorkloadType } from '@/types/enums/workloads';
import { MetricScalarResponse, TimeSeriesResponse } from '@/types/metrics';

export const listWorkloads = async (
  projectId: string,
  filters?: {
    type?: WorkloadType[];
    status?: WorkloadStatus[];
    withResources?: boolean;
  },
): Promise<Workload[]> => {
  if (!projectId) {
    throw new APIRequestError(`No project selected`, 422);
  }

  const urlParams = new URLSearchParams();
  urlParams.append('project_id', projectId);

  if (filters?.type) {
    filters.type.forEach((t) => {
      urlParams.append('type', t);
    });
  }
  if (filters?.status) {
    filters.status.forEach((s) => {
      urlParams.append('status', s);
    });
  }
  if (filters?.withResources !== undefined) {
    urlParams.append('with_resources', String(filters.withResources));
  }

  const response = await fetch(`/api/workloads?${urlParams.toString()}`, {
    method: 'GET',
  });

  if (!response.ok) {
    throw new APIRequestError(await getErrorMessage(response), response.status);
  }

  const json = await response.json();
  return json.data;
};

export const getWorkload = async (
  workloadId: string,
  withResources: boolean = false,
): Promise<Workload> => {
  const response = await fetch(
    `/api/workloads/${workloadId}?withResources=${withResources}`,
    {
      method: 'GET',
    },
  );

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to get workload: ${await getErrorMessage(response)}`,
      response.status,
    );
  }

  const json = await response.json();
  return json;
};

export const getWorkloadLogs = async (
  workloadId: string,
  params: WorkloadLogParams = {},
): Promise<WorkloadLogResponse> => {
  const urlParams = new URLSearchParams();
  if (params.startDate) urlParams.append('start_date', params.startDate);
  if (params.endDate) urlParams.append('end_date', params.endDate);
  if (params.pageToken)
    urlParams.append('page_token', params.pageToken.split('+')[0]);
  if (params.level) urlParams.append('level', params.level);
  if (params.limit) urlParams.append('limit', params.limit.toString());
  if (params.direction) urlParams.append('direction', params.direction);
  if (params.logType) urlParams.append('log_type', params.logType);

  const response = await fetch(
    `/api/workloads/${workloadId}/logs?${urlParams.toString()}`,
    {
      method: 'GET',
    },
  );

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to get workload logs: ${await getErrorMessage(response)}`,
      response.status,
    );
  }

  const json = await response.json();
  // Return logs response directly (individual resource endpoint, not wrapped)
  return json;
};

export const deleteWorkload = async (id: string) => {
  const response = await fetch(`/api/workloads/${id}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) {
    throw new Error(
      `Failed to terminate workload: ${await getErrorMessage(response)}`,
    );
  }
};

export const getClusterWorkloadsStats = async (clusterId: string) => {
  const response = await fetch(`/api/clusters/${clusterId}/workloads/stats`);
  if (!response.ok) {
    throw new APIRequestError(
      `Failed to get cluster workloads stats: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
  return response.json();
};

export const getWorkloadsStats = async () => {
  const response = await fetch(`/api/workloads/stats`);
  if (!response.ok) {
    throw new APIRequestError(
      `Failed to get workloads stats: ${await getErrorMessage(response)}`,
      response.status,
    );
  }
  return response.json();
};

export const getTimeToFirstToken = async (
  workloadId: string,
  start: Date,
  end: Date,
): Promise<TimeSeriesResponse> => {
  const urlParams = new URLSearchParams();
  urlParams.append('start', start.toISOString());
  urlParams.append('end', end.toISOString());

  const response = await fetch(
    `/api/workloads/${workloadId}/metrics/time-to-first-token/?${urlParams.toString()}`,
  );
  if (!response.ok) {
    throw new Error(
      `Failed to get workload metric: time to first token: ${await getErrorMessage(
        response,
      )}`,
    );
  }
  return response.json();
};

export const getInterTokenLatency = async (
  workloadId: string,
  start: Date,
  end: Date,
): Promise<TimeSeriesResponse> => {
  const urlParams = new URLSearchParams();
  urlParams.append('start', start.toISOString());
  urlParams.append('end', end.toISOString());

  const response = await fetch(
    `/api/workloads/${workloadId}/metrics/inter-token-latency/?${urlParams.toString()}`,
  );
  if (!response.ok) {
    throw new Error(
      `Failed to get workload metric: inter-token latency: ${await getErrorMessage(
        response,
      )}`,
    );
  }
  return response.json();
};

export const getEndToEndLatency = async (
  workloadId: string,
  start: Date,
  end: Date,
): Promise<TimeSeriesResponse> => {
  const urlParams = new URLSearchParams();
  urlParams.append('start', start.toISOString());
  urlParams.append('end', end.toISOString());

  const response = await fetch(
    `/api/workloads/${workloadId}/metrics/end-to-end-latency/?${urlParams.toString()}`,
  );
  if (!response.ok) {
    throw new Error(
      `Failed to get workload metric: end-to-end latency: ${await getErrorMessage(
        response,
      )}`,
    );
  }
  return response.json();
};

export const getInferenceRequests = async (
  workloadId: string,
  start: Date,
  end: Date,
): Promise<TimeSeriesResponse> => {
  const urlParams = new URLSearchParams();
  urlParams.append('start', start.toISOString());
  urlParams.append('end', end.toISOString());

  const response = await fetch(
    `/api/workloads/${workloadId}/metrics/inference-requests/?${urlParams.toString()}`,
  );
  if (!response.ok) {
    throw new Error(
      `Failed to get workload metric: inference requests: ${await getErrorMessage(
        response,
      )}`,
    );
  }
  return response.json();
};

export const getTotalTokens = async (
  workloadId: string,
  start: Date,
  end: Date,
): Promise<MetricScalarResponse> => {
  const urlParams = new URLSearchParams();
  urlParams.append('start', start.toISOString());
  urlParams.append('end', end.toISOString());

  const response = await fetch(
    `/api/workloads/${workloadId}/metrics/total-tokens/?${urlParams.toString()}`,
  );
  if (!response.ok) {
    throw new Error(
      `Failed to get workload metric: total tokens: ${await getErrorMessage(
        response,
      )}`,
    );
  }
  return response.json();
};

export const getKVCacheUsage = async (
  workloadId: string,
  start: Date,
  end: Date,
): Promise<MetricScalarResponse> => {
  const urlParams = new URLSearchParams();
  urlParams.append('start', start.toISOString());
  urlParams.append('end', end.toISOString());

  const response = await fetch(
    `/api/workloads/${workloadId}/metrics/kv-cache-usage/?${urlParams.toString()}`,
  );
  if (!response.ok) {
    throw new Error(
      `Failed to get workload metric: KV cache usage: ${await getErrorMessage(
        response,
      )}`,
    );
  }
  return response.json();
};
