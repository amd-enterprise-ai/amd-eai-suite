// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Select, SelectItem, Spinner, Switch } from '@heroui/react';

import { useTranslation } from 'next-i18next';

import {
  Workload,
  WorkloadLogPagination,
  WorkloadLogResponse,
} from '@/types/workloads';
import { LogLevel } from '@/types/enums/workloads';

import { useQuery } from '@tanstack/react-query';
import { getWorkloadLogs } from '@/services/app/workloads';
import { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { LogEntry } from '@/types/workloads';
import { throttle } from 'lodash';
import useSystemToast from '@/hooks/useSystemToast';
import { useWorkloadLogsStream } from '@/hooks/useWorkloadLogsStream';

interface Props {
  workload: Workload | undefined;
  isOpen: boolean;
}

const WorkloadLogs = ({ workload, isOpen }: Props) => {
  const { t } = useTranslation('workloads');

  const [isStreamingMode, setIsStreamingMode] = useState(false);
  const [selectedLogLevel, setSelectedLogLevel] = useState<string>('');
  const [currentStartDate, setCurrentStartDate] = useState<string | undefined>(
    undefined,
  );
  const [pagination, setPagination] = useState<
    WorkloadLogPagination | undefined
  >(undefined);
  const [allLogs, setAllLogs] = useState<LogEntry[]>([]);
  const logsContainerRef = useRef<HTMLDivElement>(null);
  const previousScrollTopRef = useRef<number>(0);
  const { toast } = useSystemToast();

  // Stable params for streaming to prevent unnecessary re-renders
  const streamParams = useMemo(
    () => ({
      direction: 'forward' as const,
      limit: 1000,
      level: (selectedLogLevel as LogLevel) || undefined,
    }),
    [selectedLogLevel],
  );

  // Streaming logs hook
  const {
    logs: streamLogs,
    isLoading: isStreamingLoading,
    isStreaming,
    error: streamError,
    startStreaming,
    stopStreaming,
    clearLogs: clearStreamLogs,
  } = useWorkloadLogsStream({
    workloadId: workload?.id || '',
    params: streamParams,
    autoStart: false,
  });

  const {
    data: workloadLogsResponse,
    isLoading: isLogsLoading,
    error: logsError,
  } = useQuery<WorkloadLogResponse | undefined>({
    queryKey: ['workloads', workload, currentStartDate, selectedLogLevel],
    queryFn: async () => {
      if (workload) {
        return await getWorkloadLogs(workload.id, {
          direction: 'backward',
          pageToken: currentStartDate,
          level: (selectedLogLevel as LogLevel) || undefined,
        });
      }
    },
    enabled: !!workload?.id && isOpen && !isStreamingMode,
  });

  const clearLogsData = useCallback(() => {
    setAllLogs([]);
    setPagination(undefined);
    setCurrentStartDate(undefined);
  }, []);

  const handleCleanup = useCallback(() => {
    clearLogsData();
    setSelectedLogLevel('');
    setIsStreamingMode(false);

    // Stop streaming if active
    if (isStreaming) {
      stopStreaming();
    }
    clearStreamLogs();

    if (logsContainerRef.current) {
      logsContainerRef.current.removeEventListener('scroll', handleScroll);
    }
  }, [isStreaming, stopStreaming, clearStreamLogs, clearLogsData]); // eslint-disable-line react-hooks/exhaustive-deps

  // Clean up when component unmounts or isOpen becomes false
  useEffect(() => {
    if (!isOpen) {
      handleCleanup();
    }
  }, [isOpen, handleCleanup]);

  useEffect(() => {
    if (logsError) {
      toast.error(t('notifications.logs.error', { error: logsError.message }));
    }
  }, [logsError, toast, t]);

  useEffect(() => {
    if (streamError) {
      toast.error(t('notifications.logs.error', { error: streamError }));
    }
  }, [streamError, toast, t]);

  useEffect(() => {
    if (workloadLogsResponse?.logs) {
      if (currentStartDate) {
        // This is a pagination request, append new logs
        setAllLogs((prevLogs) => [...prevLogs, ...workloadLogsResponse.logs]);
      } else {
        // This is the initial request, replace all logs
        setAllLogs(workloadLogsResponse.logs);
      }
      setPagination(workloadLogsResponse.pagination);
    }
  }, [workloadLogsResponse]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleStreamingToggle = useCallback(
    async (enabled: boolean) => {
      setIsStreamingMode(enabled);

      if (enabled) {
        // Clear pagination logs when switching to streaming
        clearLogsData();
        // Start streaming with a small delay to ensure state is updated
        if (workload?.id) {
          setTimeout(() => {
            startStreaming();
          }, 100);
        }
      } else {
        // Stop streaming when switching to pagination
        if (isStreaming) {
          stopStreaming();
        }
        clearStreamLogs();
      }
    },
    [
      workload,
      isStreaming,
      startStreaming,
      stopStreaming,
      clearStreamLogs,
      clearLogsData,
    ],
  );

  const handleLogLevelChange = useCallback(
    (logLevel: string) => {
      setSelectedLogLevel(logLevel);
      // Clear existing logs when log level filter changes
      clearLogsData();

      // If streaming is active, restart it with new log level filter
      if (isStreamingMode && isStreaming) {
        stopStreaming();
        clearStreamLogs();
        // Restart streaming after a short delay
        setTimeout(() => {
          startStreaming();
        }, 100);
      }
    },
    [
      isStreamingMode,
      isStreaming,
      stopStreaming,
      clearStreamLogs,
      startStreaming,
      clearLogsData,
    ],
  );

  const logLevelOptions = useMemo(() => {
    return [
      {
        key: '',
        label: t('list.actions.logs.modal.logLevelFilter.allLevels'),
      },
      ...Object.values(LogLevel).map((level) => ({
        key: level,
        label: level.toUpperCase(),
      })),
    ];
  }, [t]);

  // Get the appropriate logs based on mode
  const currentLogs = isStreamingMode ? streamLogs : allLogs;
  const isCurrentlyLoading = isStreaming
    ? isStreamingLoading
    : isLogsLoading && allLogs.length === 0;
  const isPaginationLoading = isStreamingMode
    ? false
    : isLogsLoading && allLogs.length > 0;

  const handleScroll = useCallback(() => {
    const container = logsContainerRef.current;
    if (!container || isLogsLoading || !pagination?.hasMore || isStreamingMode)
      return;

    const { scrollTop, scrollHeight, clientHeight } = container;
    const previousScrollTop = previousScrollTopRef.current;

    // Only trigger when scrolling down
    if (scrollTop <= previousScrollTop) {
      previousScrollTopRef.current = scrollTop;
      return;
    }

    previousScrollTopRef.current = scrollTop;
    const scrollThreshold = 100; // Trigger 100px before reaching the bottom

    if (scrollHeight - scrollTop - clientHeight < scrollThreshold) {
      const throttledLoadMore = throttle(() => {
        setCurrentStartDate(pagination?.pageToken);
      }, 300);
      throttledLoadMore();
    }
  }, [isLogsLoading, isStreamingMode, pagination]);

  useEffect(() => {
    const container = logsContainerRef.current;
    if (!container) return;

    const throttledHandleScroll = throttle(handleScroll, 100);
    container.addEventListener('scroll', throttledHandleScroll);

    return () => {
      container.removeEventListener('scroll', throttledHandleScroll);
      throttledHandleScroll.cancel();
    };
  }, [handleScroll, isStreamingMode]);

  // Auto-scroll to bottom when new streaming logs arrive
  useEffect(() => {
    if (isStreamingMode && streamLogs.length > 0) {
      const container = logsContainerRef.current;
      if (container) {
        // Small delay to ensure DOM is updated
        setTimeout(() => {
          container.scrollTop = container.scrollHeight;
        }, 10);
      }
    }
  }, [isStreamingMode, streamLogs.length]);

  if (!workload) {
    return (
      <div className="p-4 text-default-600">
        {t('list.actions.logs.modal.workloadNotFound')}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full max-h-[60vh]">
      <div className="mb-4">
        <div className="text-default-600 mb-4">
          {t('list.actions.logs.modal.description', {
            workload: workload.name,
          })}
        </div>
        {/* Log filter and streaming controls hidden: TODO(SDA-2428): re-enable them when fixed on backend */}
        <div className="hidden">
          <div>
            <Select
              size="sm"
              placeholder={t('list.actions.logs.modal.logLevelFilter.label')}
              className="min-w-[120px]"
              selectedKeys={selectedLogLevel ? [selectedLogLevel] : []}
              onSelectionChange={(keys) => {
                const selectedKey = Array.from(keys)[0] as string;
                handleLogLevelChange(selectedKey || '');
              }}
            >
              {logLevelOptions.map((option) => (
                <SelectItem key={option.key}>{option.label}</SelectItem>
              ))}
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <Switch
              isSelected={isStreamingMode}
              onValueChange={handleStreamingToggle}
              size="sm"
              color="primary"
            />
            {t('list.actions.logs.modal.streaming')}
          </div>
        </div>
      </div>
      <div
        className="bg-default-100 dark:bg-default-100 rounded-lg p-4 font-mono flex-1 overflow-y-auto min-h-0"
        ref={logsContainerRef}
        data-testid="workload-logs-container"
      >
        {isCurrentlyLoading ? (
          <div
            className="flex justify-center items-center h-64"
            data-testid="workload-logs-loading"
          >
            <Spinner size="lg" color="primary" />
          </div>
        ) : (
          <div className="space-y-1">
            {currentLogs.map((log: LogEntry, index: number) => (
              <div key={index} className="flex gap-2 text-sm">
                <span className="text-default-500 whitespace-nowrap">
                  {new Date(log.timestamp).toLocaleString()}
                </span>
                <span className={`uppercase font-semibold`}>[{log.level}]</span>
                <span className="break-all">{log.message}</span>
              </div>
            ))}

            {/* Loading indicator for infinite scroll (pagination mode only) */}
            {isPaginationLoading && (
              <div className="flex justify-center items-center py-4">
                <Spinner size="sm" color="primary" />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default WorkloadLogs;
