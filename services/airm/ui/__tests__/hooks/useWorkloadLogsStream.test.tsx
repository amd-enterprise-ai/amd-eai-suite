// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi, afterEach } from 'vitest';

import { useWorkloadLogsStream } from '../../hooks/useWorkloadLogsStream';
import * as workloadsService from '../../services/app/workloads';
import { mockWorkloadLogEntries } from '../../__mocks__/services/app/workloads.data';

import { LogEntry } from '@/types/workloads';
import { LogLevel } from '@/types/enums/workloads';

// Mock the workloads service
vi.mock('../../services/app/workloads');

describe('useWorkloadLogsStream', () => {
  const mockGetWorkloadLogsStream = vi.mocked(
    workloadsService.getWorkloadLogsStream,
  );

  // Use imported mock log entries for testing
  const [mockLogEntry1, mockLogEntry2, mockLogEntry3] = mockWorkloadLogEntries;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  describe('initial state', () => {
    it('should initialize with correct default values', () => {
      const { result } = renderHook(() =>
        useWorkloadLogsStream({
          workloadId: 'test-workload-id',
        }),
      );

      expect(result.current.logs).toEqual([]);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.isStreaming).toBe(false);
      expect(result.current.error).toBeNull();
      expect(typeof result.current.startStreaming).toBe('function');
      expect(typeof result.current.stopStreaming).toBe('function');
      expect(typeof result.current.clearLogs).toBe('function');
    });
  });

  describe('autoStart functionality', () => {
    it('should automatically start streaming when autoStart is true', async () => {
      const mockStream = createMockStream([mockLogEntry1, mockLogEntry2]);
      mockGetWorkloadLogsStream.mockResolvedValue(mockStream);

      const { result } = renderHook(() =>
        useWorkloadLogsStream({
          workloadId: 'test-workload-id',
          autoStart: true,
        }),
      );

      expect(mockGetWorkloadLogsStream).toHaveBeenCalledWith(
        'test-workload-id',
        {},
      );

      await waitFor(() => {
        expect(result.current.logs.length).toBeGreaterThan(0);
      });
    });

    it('should not start streaming when autoStart is false', () => {
      const { result } = renderHook(() =>
        useWorkloadLogsStream({
          workloadId: 'test-workload-id',
          autoStart: false,
        }),
      );

      expect(mockGetWorkloadLogsStream).not.toHaveBeenCalled();
      expect(result.current.isStreaming).toBe(false);
    });
  });

  describe('startStreaming', () => {
    it('should start streaming and accumulate log entries', async () => {
      const mockStream = createMockStream([
        mockLogEntry1,
        mockLogEntry2,
        mockLogEntry3,
      ]);
      mockGetWorkloadLogsStream.mockResolvedValue(mockStream);

      const { result } = renderHook(() =>
        useWorkloadLogsStream({
          workloadId: 'test-workload-id',
        }),
      );

      await act(async () => {
        await result.current.startStreaming();
      });

      // Wait for all logs to be processed
      await waitFor(
        () => {
          expect(result.current.logs).toHaveLength(3);
        },
        { timeout: 1000 },
      );

      expect(result.current.logs).toEqual([
        mockLogEntry1,
        mockLogEntry2,
        mockLogEntry3,
      ]);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.isStreaming).toBe(false);
    });

    it('should pass parameters to the service', async () => {
      const mockStream = createMockStream([]);
      mockGetWorkloadLogsStream.mockResolvedValue(mockStream);

      const params = {
        startDate: '2023-01-01',
        endDate: '2023-01-02',
        level: LogLevel.ERROR,
      };

      const { result } = renderHook(() =>
        useWorkloadLogsStream({
          workloadId: 'test-workload-id',
          params,
        }),
      );

      await act(async () => {
        await result.current.startStreaming();
      });

      expect(mockGetWorkloadLogsStream).toHaveBeenCalledWith(
        'test-workload-id',
        params,
      );
    });

    it('should handle service errors', async () => {
      const errorMessage = 'Failed to connect to stream';
      mockGetWorkloadLogsStream.mockRejectedValue(new Error(errorMessage));

      const { result } = renderHook(() =>
        useWorkloadLogsStream({
          workloadId: 'test-workload-id',
        }),
      );

      await act(async () => {
        await result.current.startStreaming();
      });

      await waitFor(() => {
        expect(result.current.error).toBe(errorMessage);
      });

      expect(result.current.isStreaming).toBe(false);
    });
  });

  describe('clearLogs', () => {
    it('should clear accumulated logs', async () => {
      const mockStream = createMockStream([mockLogEntry1, mockLogEntry2]);
      mockGetWorkloadLogsStream.mockResolvedValue(mockStream);

      const { result } = renderHook(() =>
        useWorkloadLogsStream({
          workloadId: 'test-workload-id',
        }),
      );

      await act(async () => {
        await result.current.startStreaming();
      });

      await waitFor(() => {
        expect(result.current.logs.length).toBeGreaterThan(0);
      });

      act(() => {
        result.current.clearLogs();
      });

      expect(result.current.logs).toEqual([]);
    });
  });

  describe('stream error handling', () => {
    it('should handle abort errors gracefully', async () => {
      const mockStream = createMockStreamWithAbortError();
      mockGetWorkloadLogsStream.mockResolvedValue(mockStream);

      const { result } = renderHook(() =>
        useWorkloadLogsStream({
          workloadId: 'test-workload-id',
        }),
      );

      await act(async () => {
        await result.current.startStreaming();
      });

      await waitFor(() => {
        expect(result.current.isStreaming).toBe(false);
      });

      // Should not set error for abort
      expect(result.current.error).toBeNull();
    });

    it('should handle read errors from stream', async () => {
      const mockStream = createMockStreamWithReadError();
      mockGetWorkloadLogsStream.mockResolvedValue(mockStream);

      const { result } = renderHook(() =>
        useWorkloadLogsStream({
          workloadId: 'test-workload-id',
        }),
      );

      await act(async () => {
        await result.current.startStreaming();
      });

      await waitFor(() => {
        expect(result.current.error).toBe('Stream read error');
      });

      expect(result.current.isStreaming).toBe(false);
    });
  });

  describe('parameter changes', () => {
    it('should restart stream when workloadId changes', async () => {
      const mockStream1 = createMockStream([mockLogEntry1]);
      const mockStream2 = createMockStream([mockLogEntry2]);

      mockGetWorkloadLogsStream
        .mockResolvedValueOnce(mockStream1)
        .mockResolvedValueOnce(mockStream2);

      const { result, rerender } = renderHook(
        ({ workloadId }) =>
          useWorkloadLogsStream({
            workloadId,
            autoStart: true,
          }),
        { initialProps: { workloadId: 'workload-1' } },
      );

      await waitFor(() => {
        expect(result.current.logs).toHaveLength(1);
      });

      rerender({ workloadId: 'workload-2' });

      await waitFor(() => {
        expect(mockGetWorkloadLogsStream).toHaveBeenCalledWith(
          'workload-2',
          {},
        );
      });
    });

    it('should restart stream when params change', async () => {
      const mockStream1 = createMockStream([mockLogEntry1]);
      const mockStream2 = createMockStream([mockLogEntry2]);

      mockGetWorkloadLogsStream
        .mockResolvedValueOnce(mockStream1)
        .mockResolvedValueOnce(mockStream2);

      const { result, rerender } = renderHook(
        ({ params }) =>
          useWorkloadLogsStream({
            workloadId: 'test-workload-id',
            params,
            autoStart: true,
          }),
        { initialProps: { params: { level: LogLevel.INFO } } },
      );

      await waitFor(() => {
        expect(result.current.logs).toHaveLength(1);
      });

      rerender({ params: { level: LogLevel.ERROR } });

      await waitFor(() => {
        expect(mockGetWorkloadLogsStream).toHaveBeenCalledWith(
          'test-workload-id',
          {
            level: LogLevel.ERROR,
          },
        );
      });
    });
  });
});

// Helper functions for creating mock streams

function createMockStream(logs: LogEntry[]): ReadableStream<LogEntry> {
  return new ReadableStream<LogEntry>({
    start(controller) {
      // Synchronously enqueue all logs and close
      logs.forEach((log) => controller.enqueue(log));
      controller.close();
    },
  });
}

function createMockStreamWithAbortError(): ReadableStream<LogEntry> {
  return new ReadableStream<LogEntry>({
    start(controller) {
      setTimeout(() => {
        const error = new Error('aborted');
        error.name = 'AbortError';
        try {
          controller.error(error);
        } catch {
          // Controller might already be closed
        }
      }, 10);
    },
  });
}

function createMockStreamWithReadError(): ReadableStream<LogEntry> {
  return new ReadableStream<LogEntry>({
    start(controller) {
      setTimeout(() => {
        try {
          controller.error(new Error('Stream read error'));
        } catch {
          // Controller might already be closed
        }
      }, 10);
    },
  });
}
