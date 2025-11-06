// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import { Cluster } from '@/types/clusters';
import { WorkloadsStats } from '@/types/workloads';

import { HorizontalStatisticsCards } from '@/components/shared/Metrics/StatisticsCard';

interface Props {
  clusters: Cluster[];
  workloadsStats: WorkloadsStats;
}

export const ClustersStats: React.FC<Props> = ({
  clusters,
  workloadsStats,
}) => {
  const { t } = useTranslation('clusters');

  const cards = useMemo(
    () => [
      {
        title: t('statistics.clusters.clusters.title'),
        tooltip: t('statistics.clusters.clusters.tooltip'),
        statistic: clusters.length,
      },
      {
        title: t('statistics.clusters.nodes.title'),
        tooltip: t('statistics.clusters.nodes.tooltip'),
        statistic: clusters.reduce(
          (partialSum, a) => partialSum + a.availableNodeCount,
          0,
        ),
        upperLimit: clusters.reduce(
          (partialSum, a) => partialSum + a.totalNodeCount,
          0,
        ),
      },
      {
        title: t('statistics.clusters.gpus.title'),
        tooltip: t('statistics.clusters.gpus.tooltip'),
        statistic: clusters.reduce(
          (partialSum, a) => partialSum + a.allocatedResources.gpuCount,
          0,
        ),
        upperLimit: clusters.reduce(
          (partialSum, a) => partialSum + a.availableResources.gpuCount,
          0,
        ),
      },
      {
        title: t('statistics.clusters.workloads.title'),
        tooltip: t('statistics.clusters.workloads.tooltip'),
        statistic: workloadsStats.runningWorkloadsCount,
      },
    ],
    [clusters, workloadsStats, t],
  );

  return <HorizontalStatisticsCards cards={cards} />;
};
