// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Select, SelectItem, Spinner, Switch } from '@heroui/react';

import { useTranslation } from 'next-i18next';

import {
  Workload,
  WorkloadLogPagination,
  WorkloadLogResponse,
} from '@amdenterpriseai/types';
import type { ResourceMetrics } from '@/types/namespaces';
import { LogLevel, LogType, WorkloadStatus } from '@amdenterpriseai/types';

import { useQuery } from '@tanstack/react-query';
import { getWorkloadLogs } from '@/lib/app/workloads';
import { getAimServiceLogs } from '@/lib/app/aims';
import { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { LogEntry } from '@amdenterpriseai/types';
import { throttle } from 'lodash';
import { useSystemToast } from '@amdenterpriseai/hooks';
import { useWorkloadLogsStream } from '@/hooks/useWorkloadLogsStream';
import Ansi from 'ansi-to-react';
import { getLogLevelColor } from '@/lib/app/logs';

export enum LogSource {
  AIM = 'aim',
  WORKLOAD = 'workload',
}

interface Props {
  workload: Workload | ResourceMetrics | undefined;
  isOpen: boolean;
  /** Log source type - defaults to 'workload' */
  logSource?: LogSource;
  namespace: string;
}

const WorkloadLogs = ({ workload, isOpen, logSource, namespace }: Props) => {
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
    data: streamLogs,
    isLoading: isStreamingLoading,
    isStreaming,
    error: streamError,
    startStreaming,
    stopStreaming,
    clearLogs: clearStreamLogs,
  } = useWorkloadLogsStream({
    namespace: namespace || '',
    workloadId: workloadId || '',
  });

  const {
    data: workloadLogsResponse,
    isLoading: isLogsLoading,
    error: logsError,
  } = useQuery<WorkloadLogResponse | undefined>({
    queryKey: [
      'workloadLogs',
      logSource,
      namespace,
      workloadId,
      currentStartDate,
      selectedLogLevel,
      selectedLogType,
    ],
    queryFn: async () => {
      if (!workloadId) return;

      const params = {
        direction: 'backward' as const,
        pageToken: currentStartDate,
        level: selectedLogLevel || undefined,
        logType: selectedLogType,
      };

      if (logSource === LogSource.AIM && namespace)
        return await getAimServiceLogs(namespace, workloadId, params);

      return await getWorkloadLogs(namespace!, workloadId, params);
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
    return Object.values(LogType).map((type) => ({
      key: type,
      label: t(`list.actions.logs.modal.logTypeFilter.${type}`),
    }));
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
    clearLogsData();
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
    if (workloadLogsResponse?.data && !isStreamingMode) {
      const sortedLogs = [...workloadLogsResponse.data].sort(
        (a, b) =>
          new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
      );

      if (currentStartDate) {
        // Store the current scroll height before adding new logs
        const container = logsContainerRef.current;
        if (container) {
          previousScrollHeightRef.current = container.scrollHeight;
        }
        // Prepend older page and re-sort so full list stays chronological (API page boundaries can mix runs)
        setAllLogs((prevLogs) => {
          const combined = [...sortedLogs, ...prevLogs];
          return combined.sort(
            (a, b) =>
              new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
          );
        });
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
    <div className="flex flex-col h-[70vh]">
      <div className="mb-4 shrink-0">
        <div className="text-default-600 mb-4">
          {t('list.actions.logs.modal.description', {
            workload: workload.displayName,
          })}
        </div>
        <div className="flex items-center gap-4">
          <div>
            <Select
              size="sm"
              aria-label={t('list.actions.logs.modal.logTypeFilter.label')}
              placeholder={t('list.actions.logs.modal.logTypeFilter.label')}
              className="min-w-[130px]"
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
              aria-label={t('list.actions.logs.modal.logLevelFilter.label')}
              placeholder={t('list.actions.logs.modal.logLevelFilter.label')}
              className="min-w-[140px]"
              selectedKeys={selectedLogLevel ? [selectedLogLevel] : []}
              onSelectionChange={(keys) => {
                const selectedKey = (Array.from(keys)[0] ?? '') as LogLevel;
                handleLogLevelChange(selectedKey);
              }}
              isDisabled={selectedLogType === LogType.EVENT}
            >
              {logLevelOptions.map((option) => (
                <SelectItem key={option.key}>{option.label}</SelectItem>
              ))}
            </Select>
          </div>
          {/* Streaming is not supported for AIM service logs */}
          {logSource !== LogSource.AIM && (
            <div className="flex items-center gap-2">
              <Switch
                isSelected={isStreamingMode}
                onValueChange={handleStreamingToggle}
                size="sm"
                color="primary"
              />
              {t('list.actions.logs.modal.streaming')}
            </div>
          )}
        </div>
      </div>
      <div
        className="bg-gray-100 dark:bg-gray-950 rounded-lg p-4 text-xs flex-1 overflow-y-auto min-h-64"
        ref={logsContainerRef}
        data-testid="workload-logs-container"
        style={{
          fontFamily:
            '"SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, "Courier New", monospace',
          fontVariantNumeric: 'tabular-nums',
        }}
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
            className="flex justify-center items-center h-64 text-gray-500"
            data-testid="workload-logs-empty"
          >
            {selectedLogType === LogType.EVENT
              ? t('list.actions.logs.modal.noEvents')
              : t('list.actions.logs.modal.noLogs')}
          </div>
        ) : (
          <div className="space-y-0 leading-relaxed">
            {currentLogs.map((log: LogEntry, index: number) => {
              const timestamp = new Date(log.timestamp).toLocaleString();

              return (
                <div
                  key={`${log.timestamp}-${index}`}
                  className="flex gap-2 hover:bg-gray-200/30 dark:hover:bg-gray-800/30"
                >
                  <span className="text-gray-400 dark:text-gray-500 shrink-0">
                    {timestamp}
                  </span>
                  {selectedLogType !== LogType.EVENT && (
                    <span
                      className="uppercase font-semibold inline-block shrink-0"
                      style={{
                        color: getLogLevelColor(log.level),
                        width: '70px',
                        textAlign: 'center',
                      }}
                    >
                      {log.level === LogLevel.UNKNOWN ? '-' : log.level}
                    </span>
                  )}
                  <div className="flex-1 break-all whitespace-pre-wrap text-gray-700 dark:text-gray-200">
                    <Ansi>{log.message}</Ansi>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default WorkloadLogs;
