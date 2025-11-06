// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getErrorMessage } from '@/utils/app/api-helpers';
import { APIRequestError } from '@/utils/app/errors';

import {
  Workload,
  WorkloadLogParams,
  WorkloadLogResponse,
  LogEntry,
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
  urlParams.append('projectId', projectId);

  if (filters?.type) {
    filters.type.forEach((t) => urlParams.append('type', t));
  }
  if (filters?.status) {
    filters.status.forEach((s) => urlParams.append('status', s));
  }
  if (filters?.withResources !== undefined) {
    urlParams.append('withResources', String(filters.withResources));
  }

  const response = await fetch(`/api/workloads?${urlParams.toString()}`, {
    method: 'GET',
  });

  if (!response.ok) {
    throw new APIRequestError(await getErrorMessage(response), response.status);
  }

  return await response.json();
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

  return await response.json();
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

  return await response.json();
};

export const getWorkloadLogsStream = async (
  workloadId: string,
  params: WorkloadLogParams = {},
): Promise<ReadableStream<LogEntry>> => {
  const urlParams = new URLSearchParams();
  if (params.startDate) urlParams.append('start_date', params.startDate);
  if (params.level) urlParams.append('level', params.level);

  const response = await fetch(
    `/api/workloads/${workloadId}/logs/stream?${urlParams.toString()}`,
    {
      method: 'GET',
      headers: {
        Accept: 'text/event-stream',
      },
    },
  );

  if (!response.ok) {
    throw new APIRequestError(
      `Failed to get workload logs stream: ${await getErrorMessage(response)}`,
      response.status,
    );
  }

  if (!response.body) {
    throw new APIRequestError(
      'Response body is null for workload logs stream',
      500,
    );
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  return new ReadableStream<LogEntry>({
    start(controller) {
      let isControllerClosed = false;
      let isControllerErrored = false;
      let chunkCount = 0;
      let buffer = ''; // Buffer for incomplete chunks

      function closeController(reason: string) {
        if (!isControllerClosed && !isControllerErrored) {
          try {
            controller.close();
            isControllerClosed = true;
          } catch (error) {
            // Controller might already be in an errored state
            console.debug(
              'Failed to close controller (expected if errored):',
              error,
            );
          }
        }
      }

      function errorController(error: any) {
        if (!isControllerClosed && !isControllerErrored) {
          console.error(
            `Erroring controller - Chunks processed: ${chunkCount}`,
            error,
          );
          try {
            controller.error(error);
            isControllerErrored = true;
          } catch (e) {
            // Controller might already be closed
            console.debug(
              'Failed to error controller (expected if closed):',
              e,
            );
          }
        }
      }

      function processSSEData(data: string) {
        if (data.trim() === '[DONE]') {
          closeController('received [DONE] marker');
          return;
        }

        try {
          const logEntry: LogEntry = JSON.parse(data);
          if (!isControllerClosed && !isControllerErrored) {
            controller.enqueue(logEntry);
          }
        } catch (error) {
          console.error('Error parsing log entry:', error, 'Raw data:', data);
        }
      }

      function processSSEChunk(chunk: string) {
        buffer += chunk;

        const events = buffer.split('\n\n');

        // Keep the last event in buffer if it might be incomplete
        // (unless it ends with \n\n, then it's complete)
        if (buffer.endsWith('\n\n')) {
          buffer = '';
        } else {
          // Last event might be incomplete, keep it in buffer
          buffer = events.pop() || '';
        }

        // Process complete events
        for (const event of events) {
          if (!event.trim()) continue;

          const lines = event.split('\n');
          let eventData = '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              // Accumulate data lines (there can be multiple)
              const lineData = line.slice(6); // Remove 'data: ' prefix
              eventData += (eventData ? '\n' : '') + lineData;
            }
          }

          if (eventData) {
            processSSEData(eventData);
          }
        }
      }

      function pump(): Promise<void> {
        return reader
          .read()
          .then(({ done, value }) => {
            chunkCount++;

            if (done || isControllerClosed || isControllerErrored) {
              if (
                buffer.trim() &&
                !isControllerClosed &&
                !isControllerErrored
              ) {
                processSSEChunk('\n\n');
              }
              closeController(
                done ? 'upstream done' : 'controller closed/errored',
              );
              return;
            }

            const chunk = decoder.decode(value, { stream: true });

            processSSEChunk(chunk);

            if (!isControllerClosed && !isControllerErrored) {
              return pump();
            }
          })
          .catch((error) => {
            console.error('Stream read error:', error);
            errorController(error);
          });
      }

      return pump();
    },
    cancel() {
      reader.cancel();
    },
  });
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
