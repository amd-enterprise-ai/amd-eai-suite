// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ChartTimeSelector } from '@/components/shared/Metrics/ChartTimeSelector';
import { TimeRangePeriod } from '@/types/enums/metrics';
import { TimeRange } from '@/types/metrics';
import { Workload } from '@/types/workloads';
import { getCurrentTimeRange } from '@/utils/app/time-range';
import { useIsFetching, useQueryClient } from '@tanstack/react-query';
import { isEqual } from 'lodash';
import React, { useCallback, useMemo, useRef, useState } from 'react';
import EndToEndLatencyCard from './EndToEndLatencyCard';
import InferenceRequestsCard from './InferenceRequestsCard';
import InterTokenLatencyCard from './InterTokenLatencyCard';
import KVCacheUsageCard from './KVCacheUsageCard';
import MaxRequestsCard from './MaxRequestsCard';
import TimeToFirstTokenCard from './TimeToFirstTokenCard';
import TotalTokensCard from './TotalTokensCard';
import { useProject } from '@/contexts/ProjectContext';
import { useTranslation } from 'next-i18next';

interface InferenceMetricsProps {
  workload: Workload;
}

export const InferenceMetrics: React.FC<InferenceMetricsProps> = ({
  workload,
}) => {
  const { t } = useTranslation(['workloads']);
  const queryClient = useQueryClient();
  const { activeProject } = useProject();

  const [timeRange, setTimeRange] = useState<TimeRange>(
    getCurrentTimeRange(TimeRangePeriod['1H']),
  );
  const currentTimePeriod = useRef<TimeRangePeriod>(TimeRangePeriod['1H']);

  const handleTimeBoundChange = (
    timePeriod: TimeRangePeriod,
    timeRange: TimeRange,
  ) => {
    currentTimePeriod.current = timePeriod as TimeRangePeriod;
    setTimeRange(timeRange);
    queryClient.invalidateQueries({
      queryKey: ['project', activeProject, 'workload', workload.id, 'metrics'],
    });
  };

  const isFetchingMetrics =
    useIsFetching({
      queryKey: ['project', activeProject, 'workload', workload.id, 'metrics'],
    }) > 0;

  const metricsLastFetchedAt = useRef<Date | undefined>(undefined);
  useMemo(() => {
    if (!isFetchingMetrics) {
      metricsLastFetchedAt.current = new Date();
    }
  }, [isFetchingMetrics]);

  const handleChartsRefresh = useCallback(() => {
    const newRange = getCurrentTimeRange(currentTimePeriod.current);
    if (isEqual(newRange, timeRange)) {
      queryClient.invalidateQueries({
        queryKey: [
          'project',
          activeProject,
          'workload',
          workload.id,
          'metrics',
        ],
      });
    } else {
      setTimeRange(newRange);
    }
  }, [timeRange, queryClient, workload.id, activeProject]);

  return (
    <>
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">
          {t('details.sections.inferenceMetrics')}
        </h3>
        <ChartTimeSelector
          onTimeRangeChange={handleTimeBoundChange}
          initialTimePeriod={TimeRangePeriod['1H']}
          translationPrefix="timeRange"
          onChartsRefresh={handleChartsRefresh}
          isFetching={isFetchingMetrics}
          lastFetchedTimestamp={metricsLastFetchedAt.current}
        />
      </div>
      <div className="flex flex-col gap-4 w-full">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:col-span-2">
          <TimeToFirstTokenCard workload={workload} timeRange={timeRange} />
          <InterTokenLatencyCard workload={workload} timeRange={timeRange} />
          <EndToEndLatencyCard workload={workload} timeRange={timeRange} />
        </div>
        <div className="flex items-start gap-4 w-full">
          <div className="grow h-full">
            <InferenceRequestsCard
              workload={workload}
              timeRange={timeRange}
              timeRangePeriod={currentTimePeriod.current}
            />
          </div>
          <div className="flex flex-col gap-4 min-w-[300px]">
            <MaxRequestsCard workload={workload} timeRange={timeRange} />
            <TotalTokensCard workload={workload} timeRange={timeRange} />
            <KVCacheUsageCard workload={workload} timeRange={timeRange} />
          </div>
        </div>
      </div>
    </>
  );
};

export default InferenceMetrics;
