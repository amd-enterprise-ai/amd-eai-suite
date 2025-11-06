// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useCallback, useEffect, useRef, useState } from 'react';

import { LogEntry, WorkloadLogParams } from '@/types/workloads';
import { getWorkloadLogsStream } from '@/services/app/workloads';

export interface UseWorkloadLogsStreamOptions {
  workloadId: string;
  params?: WorkloadLogParams;
  autoStart?: boolean;
}

export interface UseWorkloadLogsStreamReturn {
  logs: LogEntry[];
  isLoading: boolean;
  isStreaming: boolean;
  error: string | null;
  startStreaming: () => void;
  stopStreaming: () => void;
  clearLogs: () => void;
}

export const useWorkloadLogsStream = ({
  workloadId,
  params = {},
  autoStart = false,
}: UseWorkloadLogsStreamOptions): UseWorkloadLogsStreamReturn => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const readerRef = useRef<ReadableStreamDefaultReader<LogEntry> | null>(null);
  const streamRef = useRef<ReadableStream<LogEntry> | null>(null);

  const stopStreaming = useCallback(() => {
    if (readerRef.current) {
      try {
        // Cancel through the reader, which automatically unlocks the stream
        readerRef.current.cancel();
      } catch (cancelError) {
        // Ignore cancel errors - the stream might already be closed/errored
        console.debug(
          'Reader cancel error (expected if stream already closed):',
          cancelError,
        );
      } finally {
        readerRef.current = null;
      }
    }
    // Don't cancel the stream directly if it has a reader - it's already cancelled above
    streamRef.current = null;
    setIsStreaming(false);
  }, []);

  const startStreaming = useCallback(async () => {
    if (isStreaming) {
      return;
    }

    // Stop any existing stream first to prevent conflicts
    if (readerRef.current || streamRef.current) {
      console.log('[HOOK] Cleaning up existing stream before restart');
      // Inline cleanup to avoid circular dependency
      if (readerRef.current) {
        try {
          readerRef.current.cancel();
        } catch (cancelError) {
          console.debug('Reader cancel error during restart:', cancelError);
        } finally {
          readerRef.current = null;
        }
      }
      streamRef.current = null;
      // Small delay to ensure cleanup completes
      await new Promise((resolve) => setTimeout(resolve, 10));
    }

    setIsStreaming(true);
    setIsLoading(true);
    setError(null);

    try {
      const stream = await getWorkloadLogsStream(workloadId, params);
      streamRef.current = stream;
      const reader = stream.getReader();
      readerRef.current = reader;
      setIsLoading(false);

      while (true) {
        try {
          const { done, value } = await reader.read();

          if (done) {
            break;
          }

          setLogs((prevLogs) => [...prevLogs, value]);
        } catch (readError) {
          // Handle read errors (e.g., stream cancelled)
          const errorMessage =
            readError instanceof Error ? readError.message : String(readError);
          const errorName = readError instanceof Error ? readError.name : '';

          if (
            errorName === 'AbortError' ||
            errorMessage.includes('cancelled')
          ) {
            // Stream was cancelled, this is expected
            break;
          } else {
            throw readError;
          }
        }
      }
    } catch (err) {
      // Only set error if it's not a cancellation
      if (
        err instanceof Error &&
        !err.message.includes('cancelled') &&
        !err.message.includes('aborted') &&
        err.name !== 'AbortError'
      ) {
        setError(err.message);
      }
    } finally {
      setIsStreaming(false);
      readerRef.current = null;
      streamRef.current = null;
    }
  }, [workloadId, JSON.stringify(params)]); // Use JSON.stringify to make params dependency stable

  const clearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  useEffect(() => {
    if (autoStart) {
      startStreaming();
    }

    return () => {
      stopStreaming();
    };
  }, [autoStart, startStreaming, stopStreaming]);

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
