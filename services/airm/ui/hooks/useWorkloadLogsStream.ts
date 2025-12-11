// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useCallback, useEffect, useRef, useState } from 'react';

import { LogEntry, WorkloadLogParams } from '@/types/workloads';

export interface UseWorkloadLogsStreamOptions {
  workloadId: string;
}

export interface UseWorkloadLogsStreamReturn {
  logs: LogEntry[];
  isLoading: boolean;
  isStreaming: boolean;
  error: string | null;
  startStreaming: (params: WorkloadLogParams) => void;
  stopStreaming: () => void;
  clearLogs: () => void;
}

/**
 * Build SSE stream URL with query parameters
 */
const buildStreamUrl = (
  workloadId: string,
  params: WorkloadLogParams = {},
): string => {
  const urlParams = new URLSearchParams();
  if (params.startDate) urlParams.append('start_date', params.startDate);
  if (params.level) urlParams.append('level', params.level);
  if (params.logType) urlParams.append('log_type', params.logType);

  const queryString = urlParams.toString();
  return `/api/workloads/${workloadId}/logs/stream${queryString ? `?${queryString}` : ''}`;
};

export const useWorkloadLogsStream = ({
  workloadId,
}: UseWorkloadLogsStreamOptions): UseWorkloadLogsStreamReturn => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const paramsRef = useRef<WorkloadLogParams>({});

  const stopStreaming = useCallback(() => {
    if (eventSourceRef.current) {
      console.debug('[SSE] Stopping stream');
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    setIsStreaming(false);
    setIsLoading(false);
  }, []);

  const connect = useCallback(
    (params: WorkloadLogParams) => {
      paramsRef.current = params;
      // Close existing connection if any
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }

      const url = buildStreamUrl(workloadId, params);
      console.debug('[SSE] Connecting to:', url);

      setIsStreaming(true);
      setIsLoading(true);
      setLogs([]);

      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.debug('[SSE] Connection opened');
        setIsLoading(false);
        setError(null);
      };

      eventSource.onmessage = (event) => {
        try {
          // Handle special markers
          if (event.data === '[DONE]') {
            console.debug('[SSE] Received [DONE] marker, closing connection');
            stopStreaming();
            return;
          } else if (event.data === '[HEARTBEAT]') {
            return;
          }

          const logEntry: LogEntry = JSON.parse(event.data);
          setLogs((prev) => [...prev, logEntry]);
        } catch (err: any) {
          console.error('[SSE] Failed to parse message:', err);
          setError(`[SSE] Failed to parse message ${err?.message}`);
        }
      };

      eventSource.onerror = (event) => {
        console.error('[SSE] Connection error:', event);
        stopStreaming();
        setError('Log streaming connection error. Please try again later.');
      };
    },
    [workloadId, stopStreaming],
  );

  const startStreaming = useCallback(
    (params: WorkloadLogParams = {}) => {
      // Prevent starting if already connected
      if (isStreaming && eventSourceRef.current) {
        console.debug('[SSE] Already connected, ignoring start request');
        return;
      }

      connect(params);
    },
    [isStreaming, connect],
  );

  const clearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopStreaming();
    };
  }, [stopStreaming]);

  return {
    logs,
    isLoading,
    isStreaming,
    error,
    startStreaming,
    stopStreaming,
    clearLogs,
  };
};
