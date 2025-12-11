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
import { LogLevel, LogType, WorkloadStatus } from '@/types/enums/workloads';

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
  const [selectedLogLevel, setSelectedLogLevel] = useState<LogLevel>(
    '' as LogLevel,
  );
  const [selectedLogType, setSelectedLogType] = useState<LogType>(() =>
    workload?.status === WorkloadStatus.PENDING
      ? LogType.EVENT
      : LogType.WORKLOAD,
  );
  const [currentStartDate, setCurrentStartDate] = useState<string | undefined>(
    undefined,
  );
  const [pagination, setPagination] = useState<
    WorkloadLogPagination | undefined
  >(undefined);
  const [allLogs, setAllLogs] = useState<LogEntry[]>([]);
  const logsContainerRef = useRef<HTMLDivElement>(null);
  const previousScrollTopRef = useRef<number>(0);
  const previousScrollHeightRef = useRef<number>(0);
  const { toast } = useSystemToast();
  const workloadId = workload?.id;

  const streamParams = useMemo(
    () => ({
      direction: 'forward' as const,
      limit: 1000,
      level: selectedLogLevel || undefined,
      logType: selectedLogType,
    }),
    [selectedLogLevel, selectedLogType],
  );

  const {
    logs: streamLogs,
    isLoading: isStreamingLoading,
    isStreaming,
    error: streamError,
    startStreaming,
    stopStreaming,
    clearLogs: clearStreamLogs,
  } = useWorkloadLogsStream({
    workloadId: workloadId || '',
  });

  const {
    data: workloadLogsResponse,
    isLoading: isLogsLoading,
    error: logsError,
  } = useQuery<WorkloadLogResponse | undefined>({
    queryKey: [
      'workloads',
      workload,
      currentStartDate,
      selectedLogLevel,
      selectedLogType,
    ],
    queryFn: async () => {
      if (workloadId) {
        return await getWorkloadLogs(workloadId, {
          direction: 'backward',
          pageToken: currentStartDate,
          level: selectedLogLevel || undefined,
          logType: selectedLogType,
        });
      }
    },
    enabled: !!workloadId && isOpen && !isStreamingMode,
  });

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

  const logTypeOptions = useMemo(() => {
    return [
      {
        key: LogType.WORKLOAD,
        label: t('list.actions.logs.modal.logTypeFilter.workload'),
      },
      {
        key: LogType.EVENT,
        label: t('list.actions.logs.modal.logTypeFilter.event'),
      },
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

    const { scrollTop } = container;
    const previousScrollTop = previousScrollTopRef.current;

    // Only trigger when scrolling up
    if (scrollTop >= previousScrollTop) {
      previousScrollTopRef.current = scrollTop;
      return;
    }

    previousScrollTopRef.current = scrollTop;
    const scrollThreshold = 100; // Trigger 100px before reaching the top

    if (scrollTop < scrollThreshold) {
      const throttledLoadMore = throttle(() => {
        setCurrentStartDate(pagination?.pageToken);
      }, 300);
      throttledLoadMore();
    }
  }, [isLogsLoading, isStreamingMode, pagination]);

  const clearLogsData = useCallback(() => {
    setAllLogs([]);
    setPagination(undefined);
    setCurrentStartDate(undefined);
  }, []);

  const handleCleanup = useCallback(() => {
    clearLogsData();
    setSelectedLogLevel('' as LogLevel);
    setSelectedLogType(
      workload?.status === WorkloadStatus.PENDING
        ? LogType.EVENT
        : LogType.WORKLOAD,
    );
    setIsStreamingMode(false);

    stopStreaming();
    clearStreamLogs();

    if (logsContainerRef.current) {
      logsContainerRef.current.removeEventListener('scroll', handleScroll);
    }
  }, [
    workload?.status,
    stopStreaming,
    clearStreamLogs,
    clearLogsData,
    handleScroll,
  ]);

  const handleLogTypeChange = (logType: string) => {
    setSelectedLogType(logType as LogType);
  };

  // Clean up when component unmounts or isOpen becomes false
  useEffect(() => {
    if (!isOpen) {
      handleCleanup();
    }
  }, [isOpen, handleCleanup]);

  /**
   * Error notifications for non-streaming error and streaming errors.
   */
  useEffect(() => {
    if (logsError) {
      toast.error(t('notifications.logs.error', { error: logsError.message }));
    }
    if (streamError) {
      toast.error(t('notifications.logs.error', { error: streamError }));
    }
  }, [logsError, streamError, toast, t]);

  /**
   * Handle the non-streaming logs and its pagination.
   */
  useEffect(() => {
    if (workloadLogsResponse?.logs && !isStreamingMode) {
      const sortedLogs = [...workloadLogsResponse.logs].sort(
        (a, b) =>
          new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
      );

      if (currentStartDate) {
        // Store the current scroll height before adding new logs
        const container = logsContainerRef.current;
        if (container) {
          previousScrollHeightRef.current = container.scrollHeight;
        }
        // This is a pagination request, prepend new logs
        setAllLogs((prevLogs) => [...sortedLogs, ...prevLogs]);
      } else {
        // This is the initial request, replace all logs
        setAllLogs(sortedLogs);
      }
      setPagination(workloadLogsResponse.pagination);
    }
  }, [workloadLogsResponse, isStreamingMode, currentStartDate]);

  const handleStreamingToggle = async (enabled: boolean) => {
    setIsStreamingMode(enabled);
  };

  const handleLogLevelChange = (logLevel: LogLevel) => {
    setSelectedLogLevel(logLevel);
  };

  /**
   * The actual streaming logs handler, which is called when the streaming mode is toggled or the log level is changed.
   */
  useEffect(() => {
    if (!isStreamingMode || !workloadId) {
      stopStreaming();
      return;
    }

    if (isStreaming) {
      stopStreaming();
      clearStreamLogs();
    }

    startStreaming(streamParams);
  }, [isStreamingMode, selectedLogLevel, selectedLogType]);

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

  // Auto-scroll to bottom when logs are loaded in pagination mode
  useEffect(() => {
    if (!isStreamingMode && allLogs.length > 0 && !currentStartDate) {
      const container = logsContainerRef.current;
      if (container) {
        // Small delay to ensure DOM is updated
        setTimeout(() => {
          container.scrollTop = container.scrollHeight;
        }, 10);
      }
    }
  }, [isStreamingMode, allLogs.length, currentStartDate]);

  // Restore scroll position after loading more logs (pagination)
  useEffect(() => {
    if (!isStreamingMode && currentStartDate && allLogs.length > 0) {
      const container = logsContainerRef.current;
      if (container && previousScrollHeightRef.current > 0) {
        // Calculate the difference in scroll height and adjust scroll position
        setTimeout(() => {
          const heightDifference =
            container.scrollHeight - previousScrollHeightRef.current;
          container.scrollTop = container.scrollTop + heightDifference;
          previousScrollHeightRef.current = 0; // Reset
        }, 10);
      }
    }
  }, [isStreamingMode, currentStartDate, allLogs.length]);

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
            workload: workload.displayName,
          })}
        </div>
        <div className="flex items-center gap-4">
          <div>
            <Select
              size="sm"
              placeholder={t('list.actions.logs.modal.logTypeFilter.label')}
              className="min-w-[120px]"
              selectedKeys={[selectedLogType]}
              onSelectionChange={(keys) => {
                const selectedKey = Array.from(keys)[0] as string;
                handleLogTypeChange(selectedKey);
              }}
            >
              {logTypeOptions.map((option) => (
                <SelectItem key={option.key}>{option.label}</SelectItem>
              ))}
            </Select>
          </div>
          <div>
            <Select
              size="sm"
              placeholder={t('list.actions.logs.modal.logLevelFilter.label')}
              className="min-w-[120px]"
              selectedKeys={selectedLogLevel ? [selectedLogLevel] : []}
              onSelectionChange={(keys) => {
                const selectedKey = (Array.from(keys)[0] ?? '') as LogLevel;
                handleLogLevelChange(selectedKey);
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
        className="bg-default-100 dark:bg-default-100 rounded-lg p-4 font-mono flex-1 overflow-y-auto min-h-64"
        ref={logsContainerRef}
        data-testid="workload-logs-container"
      >
        {/* Loading indicator for infinite scroll (pagination mode only) */}
        {isPaginationLoading && (
          <div className="flex justify-center items-center py-4">
            <Spinner size="sm" color="primary" />
          </div>
        )}
        {isCurrentlyLoading ? (
          <div
            className="flex justify-center items-center h-64"
            data-testid="workload-logs-loading"
          >
            <Spinner size="lg" color="primary" />
          </div>
        ) : currentLogs.length === 0 ? (
          <div
            className="flex justify-center items-center h-64 text-default-500"
            data-testid="workload-logs-empty"
          >
            {t('list.actions.logs.modal.noLogs')}
          </div>
        ) : (
          <div className="space-y-1">
            {currentLogs.map((log: LogEntry, index: number) => (
              <div key={index} className="flex gap-2 text-sm">
                <span className="text-default-500 whitespace-nowrap">
                  {new Date(log.timestamp).toLocaleString()}
                </span>
                <span className="uppercase font-semibold">{log.level}</span>
                <span className="break-all">{log.message}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default WorkloadLogs;
