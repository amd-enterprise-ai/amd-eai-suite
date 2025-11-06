// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import { displayPercentage } from '@/utils/app/strings';

import { MetricScalarResponse, TimeRange } from '@/types/metrics';

import { StatisticsCard } from '@/components/shared/Metrics/StatisticsCard';
import { Workload } from '@/types/workloads';
import { getKVCacheUsage } from '@/services/app/workloads';
import { WorkloadType, WorkloadStatus } from '@/types/enums/workloads';
import { useQuery } from '@tanstack/react-query';
import { useProject } from '@/contexts/ProjectContext';

interface Props {
  workload: Workload;
  timeRange: TimeRange;
}

export const KVCacheUsageCard: React.FC<Props> = ({ workload, timeRange }) => {
  const { t } = useTranslation('workloads');
  const { activeProject } = useProject();

  const { data: kvCacheUsageData, isLoading: isKvCacheUsageLoading } =
    useQuery<MetricScalarResponse>({
      queryKey: [
        'project',
        activeProject,
        'workload',
        workload.id,
        'metrics',
        'kvCacheUsage',
        {
          start: timeRange.start.toISOString(),
          end: timeRange.end.toISOString(),
        },
      ],
      queryFn: () =>
        getKVCacheUsage(workload.id as string, timeRange.start, timeRange.end),
      enabled:
        !!workload.id &&
        workload?.type === WorkloadType.INFERENCE &&
        workload?.status === WorkloadStatus.RUNNING,
    });

  const kvCacheUsage = useMemo(() => {
    const value = kvCacheUsageData?.data ?? 0;
    return value * 100;
  }, [kvCacheUsageData]);

  return (
    <StatisticsCard
      title={t('details.metrics.kvCacheUsage.title')}
      tooltip={t('details.metrics.kvCacheUsage.description')}
      statistic={kvCacheUsage}
      statisticFormatter={displayPercentage}
      isLoading={isKvCacheUsageLoading}
    />
  );
};

export default KVCacheUsageCard;
