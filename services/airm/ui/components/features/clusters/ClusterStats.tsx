// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import { Cluster } from '@/types/clusters';
import { WorkloadsStats } from '@/types/workloads';

import { HorizontalStatisticsCards } from '@/components/shared/Metrics/StatisticsCard';

interface Props {
  cluster: Cluster;
  workloadsStats: WorkloadsStats;
}

export const ClusterStats: React.FC<Props> = ({ cluster, workloadsStats }) => {
  const { t } = useTranslation('clusters');

  const cards = useMemo(
    () => [
      {
        title: t('statistics.cluster.nodes.title'),
        tooltip: t('statistics.cluster.nodes.tooltip'),
        statistic: cluster.availableNodeCount,
        upperLimit: cluster.totalNodeCount,
      },
      {
        title: t('statistics.cluster.projects.title'),
        tooltip: t('statistics.cluster.projects.tooltip'),
        statistic: cluster.assignedQuotaCount,
      },
      {
        title: t('statistics.cluster.gpus.title'),
        tooltip: t('statistics.cluster.gpus.tooltip'),
        statistic: cluster.allocatedResources.gpuCount,
        upperLimit: cluster.availableResources.gpuCount,
      },
      {
        title: t('statistics.cluster.workloads.title'),
        tooltip: t('statistics.cluster.workloads.tooltip'),
        statistic: workloadsStats.runningWorkloadsCount,
      },
    ],
    [cluster, workloadsStats, t],
  );

  return <HorizontalStatisticsCards cards={cards} />;
};
