// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import { StatisticsCard } from '@/components/shared/Metrics/StatisticsCard';
import { TimeRange, TimeSeriesResponse } from '@/types/metrics';
import { Workload } from '@/types/workloads';
import { getInferenceRequests } from '@/services/app/workloads';
import { WorkloadType, WorkloadStatus } from '@/types/enums/workloads';
import { useQuery } from '@tanstack/react-query';
import { useProject } from '@/contexts/ProjectContext';
import { transformTimeSeriesDataToChartData } from '@/utils/app/charts';

interface Props {
  workload: Workload;
  timeRange: TimeRange;
}

export const MaxRequestsCard: React.FC<Props> = ({ workload, timeRange }) => {
  const { t } = useTranslation('workloads');
  const { activeProject } = useProject();

  const { data: inferenceRequestsData, isLoading: isInferenceRequestsLoading } =
    useQuery<TimeSeriesResponse>({
      queryKey: [
        'project',
        activeProject,
        'workload',
        workload.id,
        'metrics',
        'inferenceRequests',
        {
          start: timeRange.start.toISOString(),
          end: timeRange.end.toISOString(),
        },
      ],
      queryFn: () =>
        getInferenceRequests(
          workload.id as string,
          timeRange.start,
          timeRange.end,
        ),
      enabled:
        !!workload.id &&
        workload?.type === WorkloadType.INFERENCE &&
        workload?.status === WorkloadStatus.RUNNING,
    });

  const inferenceRequestsChartData = useMemo(() => {
    if (!inferenceRequestsData?.data) return null;

    const mappedData = inferenceRequestsData.data.map((item) => ({
      ...item,
      metadata: {
        ...item.metadata,
        metric: item.metadata.label,
      },
    }));

    return transformTimeSeriesDataToChartData(
      mappedData,
      inferenceRequestsData.range.timestamps,
      'metric',
    );
  }, [inferenceRequestsData]);

  const maxRequests = useMemo(() => {
    return (
      inferenceRequestsChartData?.data?.reduce((max: number, item: any) => {
        const runningRequests = item.running_requests ?? 0;
        const waitingRequests = item.waiting_requests ?? 0;
        return runningRequests + waitingRequests > max
          ? runningRequests + waitingRequests
          : max;
      }, 0) ?? 0
    );
  }, [inferenceRequestsChartData]);

  return (
    <StatisticsCard
      title={t('details.metrics.maxRequests.title')}
      tooltip={t('details.metrics.maxRequests.description')}
      statistic={maxRequests}
      isLoading={isInferenceRequestsLoading}
    />
  );
};

export default MaxRequestsCard;
