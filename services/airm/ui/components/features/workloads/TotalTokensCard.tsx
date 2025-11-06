// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import { formatTokens } from '@/utils/app/strings';

import { MetricScalarResponse, TimeRange } from '@/types/metrics';

import { StatisticsCard } from '@/components/shared/Metrics/StatisticsCard';
import { Workload } from '@/types/workloads';
import { getTotalTokens } from '@/services/app/workloads';
import { WorkloadType, WorkloadStatus } from '@/types/enums/workloads';
import { useQuery } from '@tanstack/react-query';
import { useProject } from '@/contexts/ProjectContext';

interface Props {
  workload: Workload;
  timeRange: TimeRange;
}

export const TotalTokensCard: React.FC<Props> = ({ workload, timeRange }) => {
  const { t } = useTranslation('workloads');
  const { activeProject } = useProject();

  const { data: totalTokensData, isLoading: isTotalTokensLoading } =
    useQuery<MetricScalarResponse>({
      queryKey: [
        'project',
        activeProject,
        'workload',
        workload.id,
        'metrics',
        'totalTokens',
        {
          start: timeRange.start.toISOString(),
          end: timeRange.end.toISOString(),
        },
      ],
      queryFn: () =>
        getTotalTokens(workload.id as string, timeRange.start, timeRange.end),
      enabled:
        !!workload.id &&
        workload?.type === WorkloadType.INFERENCE &&
        workload?.status === WorkloadStatus.RUNNING,
    });

  const totalTokens = useMemo(() => {
    return totalTokensData?.data ?? 0;
  }, [totalTokensData]);

  return (
    <StatisticsCard
      title={t('details.metrics.totalTokens.title')}
      tooltip={t('details.metrics.totalTokens.description')}
      statistic={totalTokens}
      statisticFormatter={formatTokens}
      isLoading={isTotalTokensLoading}
    />
  );
};

export default TotalTokensCard;
