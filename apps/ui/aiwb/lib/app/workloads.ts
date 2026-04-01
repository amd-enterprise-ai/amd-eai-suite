// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  CatalogItem,
  CatalogItemDeployment,
  CollectionRequestParams,
  PlotPoint,
  TimeRangePeriod,
  TimeSeriesData,
  Workload,
  WorkloadLogParams,
  WorkloadLogResponse,
  WorkloadStatus,
  WorkloadType,
} from '@amdenterpriseai/types';
import {
  APIRequestError,
  buildQueryParams,
  convertCamelToSnake,
  getErrorMessage,
} from '@amdenterpriseai/utils/app';

export type WorkloadsResponse = {
  data: Workload[];
  total: number;
  page: number;
  pageSize: number;
};

export const listWorkloads = async (
  projectId: string,
  filters?: {
    type?: WorkloadType[];
    status?: WorkloadStatus[];
  },
  collectionRequestParams?: CollectionRequestParams<Workload>,
): Promise<WorkloadsResponse> => {
  if (!projectId) {
    throw new APIRequestError('No project selected', 422);
  }

  const urlParams = new URLSearchParams();

  if (filters?.type) {
    filters.type.forEach((t) => {
      urlParams.append('workload_type', t);
    });
  }
  if (filters?.status) {
    filters.status.forEach((s) => {
      urlParams.append('status_filter', s);
    });
  }
  const paginationParams = collectionRequestParams
    ? buildQueryParams(
        collectionRequestParams.page,
        collectionRequestParams.pageSize,
        collectionRequestParams.filter,
        collectionRequestParams.sort,
      )
    : '';

  const response = await fetch(
    `/api/namespaces/${projectId}/workloads?${urlParams.toString()}${paginationParams}`,
    {
      method: 'GET',
    },
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to list workloads: ${errorMessage}`,
      response.status,
    );
  }

  return await response.json();
};

export const getWorkload = async (
  workloadId: string,
  projectId?: string,
): Promise<Workload> => {
  if (!projectId) {
    throw new APIRequestError('No project selected', 422);
  }

  const response = await fetch(
    `/api/namespaces/${projectId}/workloads/${workloadId}`,
    {
      method: 'GET',
    },
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get workload: ${errorMessage}`,
      response.status,
    );
  }

  const json = await response.json();
  return json;
};

export const getWorkloadMetrics = async (
  workloadId: string,
  projectId: string,
  start: Date,
  end: Date,
  metric: string,
): Promise<any> => {
  if (!projectId) {
    throw new APIRequestError('No project selected', 422);
  }

  const urlParams = new URLSearchParams();
  urlParams.append('start', start.toISOString());
  urlParams.append('end', end.toISOString());

  const response = await fetch(
    `/api/namespaces/${projectId}/workloads/${workloadId}/metrics/${metric}?${urlParams.toString()}`,
    {
      method: 'GET',
    },
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get workload metrics: ${errorMessage}`,
      response.status,
    );
  }

  const json = await response.json();
  return json;
};

export const deleteWorkload = async (id: string, projectId: string) => {
  const response = await fetch(`/api/namespaces/${projectId}/workloads/${id}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to terminate workload: ${errorMessage}`,
      response.status,
    );
  }
};

export const getWorkloadLogs = async (
  namespace: string,
  workloadId: string,
  params: WorkloadLogParams = {},
): Promise<WorkloadLogResponse> => {
  const urlParams = new URLSearchParams();

  // Workload logs endpoint requires 'start' and 'end' parameters (ISO format)
  // Default to last 24 hours if not provided
  const end = params.endDate ? new Date(params.endDate) : new Date();
  const start = params.startDate
    ? new Date(params.startDate)
    : new Date(end.getTime() - 24 * 60 * 60 * 1000);

  urlParams.append('start', start.toISOString());
  urlParams.append('end', end.toISOString());

  if (params.pageToken) {
    // Ensure the pageToken has timezone info
    let pageToken = params.pageToken;
    // If it doesn't end with 'Z' or contain timezone offset (+/-), assume UTC and add 'Z'
    if (!pageToken.endsWith('Z') && !/[+-]\d{2}:\d{2}$/.test(pageToken)) {
      pageToken = pageToken + 'Z';
    }
    urlParams.append('page_token', pageToken);
  }
  if (params.level) urlParams.append('level', params.level);
  if (params.limit) urlParams.append('limit', params.limit.toString());
  if (params.direction) urlParams.append('direction', params.direction);
  if (params.logType) urlParams.append('log_type', params.logType);
  const response = await fetch(
    `/api/namespaces/${namespace}/workloads/${workloadId}/logs?${urlParams.toString()}`,
    {
      method: 'GET',
    },
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get workload logs: ${errorMessage}`,
      response.status,
    );
  }

  const json = await response.json();
  // Return logs response directly (individual resource endpoint, not wrapped)
  return json;
};

/**
 * Transforms time series data into chart-ready format with data points and categories.
 *
 * @param tsd - Array of time series data entries
 * @param timestamps - Array of timestamp strings for the x-axis
 * @param metadataKey - Key in metadata to use for category names
 * @returns Object with data array and categories array
 */
export const transformTimeSeriesDataToChartData = (
  tsd: TimeSeriesData[],
  timestamps: string[],
  metadataKey: string,
) => {
  return {
    data: timestamps.map((timestamp) => {
      return tsd.reduce(
        (acc: PlotPoint, group) => {
          const matchingData = group.values.find(
            (entry) => entry.timestamp === timestamp,
          );
          const meta = group.metadata[metadataKey];
          const categoryName =
            typeof meta === 'object' && meta !== null && 'name' in meta
              ? (meta as { name: string }).name
              : String(meta);
          acc[categoryName] = matchingData ? matchingData.value : 0;
          return acc;
        },
        { date: timestamp },
      );
    }),
    categories: tsd.map((data) => {
      const meta = data.metadata[metadataKey];
      return typeof meta === 'object' && meta !== null && 'name' in meta
        ? (meta as { name: string }).name
        : String(meta);
    }),
  };
};

/**
 * Returns the tick gap for chart x-axis based on time range period.
 * Used to reduce label density for shorter time ranges (1h, 24h).
 *
 * @param timePeriodRange - The selected time range period
 * @returns Tick gap value (36) for 1h/24h, undefined otherwise
 */
export const getTickGap = (
  timePeriodRange?: TimeRangePeriod,
): number | undefined => {
  return timePeriodRange === TimeRangePeriod['24H'] ||
    timePeriodRange === TimeRangePeriod['1H']
    ? 36
    : undefined;
};

export const deployWorkspace = async (
  namespace: string,
  payload: CatalogItemDeployment,
): Promise<{
  id: string;
}> => {
  const {
    template,
    displayName,
    gpus,
    memoryPerGpu,
    cpuPerGpu,
    image,
    imagePullSecrets,
  } = payload;

  const url = `/api/namespaces/${namespace}/workspaces/${template}?display_name=${displayName}`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(
      convertCamelToSnake({
        gpus,
        memoryPerGpu,
        cpuPerGpu,
        image,
        imagePullSecrets,
      }),
    ),
  });

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to deploy catalog item: ${errorMessage}`,
      response.status,
    );
  }

  return await response.json();
};

export const getCatalogItems = async (
  type?: WorkloadType,
): Promise<CatalogItem[]> => {
  const urlParams = new URLSearchParams();
  if (type) {
    urlParams.append('type', type);
  }

  const url = `/api/charts${urlParams.toString() ? `?${urlParams.toString()}` : ''}`;

  const response = await fetch(url);

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch catalog items: ${errorMessage}`,
      response.status,
    );
  }

  const catalogResponse = await response.json();

  return catalogResponse.data;
};

export const getCatalogItemById = async (id: string): Promise<CatalogItem> => {
  const url = `/api/charts/${id}`;

  const response = await fetch(url);

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch catalog item: ${errorMessage}`,
      response.status,
    );
  }

  return await response.json();
};
