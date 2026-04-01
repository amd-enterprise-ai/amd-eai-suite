// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { MetricScalarResponse, TimeSeriesResponse } from '@/types/metrics';
import { APIRequestError, getErrorMessage } from '@amdenterpriseai/utils/app';

type MetricTimeRangeParams = {
  workloadId: string;
  namespace: string;
  start: Date;
  end: Date;
};

export const getTimeseriesMetric = async (
  params: MetricTimeRangeParams & { metric: string },
): Promise<TimeSeriesResponse> => {
  const { workloadId, namespace, start, end, metric } = params;
  const urlParams = new URLSearchParams();
  urlParams.append('start', start.toISOString());
  urlParams.append('end', end.toISOString());

  const metricPath = `aims/services/${workloadId}/metrics/${metric}`;
  const response = await fetch(
    `/api/namespaces/${namespace}/${metricPath}?${urlParams.toString()}`,
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get workload metric: ${metric}: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

export const getScalarMetric = async (
  params: MetricTimeRangeParams & { metric: string },
): Promise<MetricScalarResponse> => {
  const { workloadId, namespace, start, end, metric } = params;
  const urlParams = new URLSearchParams();
  urlParams.append('start', start.toISOString());
  urlParams.append('end', end.toISOString());

  const metricPath = `aims/services/${workloadId}/metrics/${metric}`;
  const response = await fetch(
    `/api/namespaces/${namespace}/${metricPath}?${urlParams.toString()}`,
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get workload metric: ${metric}: ${errorMessage}`,
      response.status,
    );
  }
  return response.json();
};

// Timeseries metric wrappers
export const getTimeToFirstToken = (params: MetricTimeRangeParams) =>
  getTimeseriesMetric({ ...params, metric: 'time_to_first_token_seconds' });

export const getInterTokenLatency = (params: MetricTimeRangeParams) =>
  getTimeseriesMetric({ ...params, metric: 'inter_token_latency_seconds' });

export const getEndToEndLatency = (params: MetricTimeRangeParams) =>
  getTimeseriesMetric({ ...params, metric: 'e2e_request_latency_seconds' });

export const getInferenceRequests = (params: MetricTimeRangeParams) =>
  getTimeseriesMetric({ ...params, metric: 'requests' });

// Scalar metric wrappers
export const getMaxRequests = (params: MetricTimeRangeParams) =>
  getScalarMetric({ ...params, metric: 'max_requests' });

export const getMinRequests = (params: MetricTimeRangeParams) =>
  getScalarMetric({ ...params, metric: 'min_requests' });

export const getAvgRequests = (params: MetricTimeRangeParams) =>
  getScalarMetric({ ...params, metric: 'avg_requests' });

export const getTotalRequests = (params: MetricTimeRangeParams) =>
  getScalarMetric({ ...params, metric: 'total_requests' });

export const getTotalTokens = (params: MetricTimeRangeParams) =>
  getScalarMetric({ ...params, metric: 'total_tokens' });

export const getKVCacheUsage = (params: MetricTimeRangeParams) =>
  getScalarMetric({ ...params, metric: 'kv_cache_usage' });
