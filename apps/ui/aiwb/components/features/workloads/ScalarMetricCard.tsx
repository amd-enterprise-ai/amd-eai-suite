// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import { StatisticsCard } from '@amdenterpriseai/components';
import { MetricScalarResponse, TimeRange } from '@amdenterpriseai/types';
import { getScalarMetric } from '@/lib/app/metrics';
import { useQuery } from '@tanstack/react-query';
import { useProject } from '@/contexts/ProjectContext';

export interface ScalarMetricConfig {
  /** Backend metric slug (e.g. 'max_requests') */
  metric: string;
  /** Locale key under details.metrics (e.g. 'maxRequests') */
  localeKey: string;
  /** Transform raw scalar before display (default: Math.round) */
  transform?: (value: number) => number;
  /** Optional display formatter passed to StatisticsCard */
  formatter?: (value: number) => string;
}

interface Props {
  config: ScalarMetricConfig;
  namespace: string;
  workloadId: string;
  timeRange: TimeRange;
}

const defaultTransform = (v: number) => Math.round(v);

export const ScalarMetricCard: React.FC<Props> = ({
  config,
  namespace,
  workloadId,
  timeRange,
}) => {
  const { t } = useTranslation('workloads');
  const { activeProject } = useProject();
  const { metric, localeKey, transform = defaultTransform, formatter } = config;

  const { data, isLoading } = useQuery<MetricScalarResponse>({
    queryKey: [
      'project',
      activeProject,
      'workload',
      workloadId,
      'metrics',
      metric,
      {
        start: timeRange.start.toISOString(),
        end: timeRange.end.toISOString(),
      },
    ],
    queryFn: () =>
      getScalarMetric({
        workloadId,
        namespace,
        start: timeRange.start,
        end: timeRange.end,
        metric,
      }),
  });

  const statistic = useMemo(
    () => transform(data?.data ?? 0),
    [data, transform],
  );

  return (
    <StatisticsCard
      title={t(`details.metrics.${localeKey}.title`)}
      tooltip={t(`details.metrics.${localeKey}.description`)}
      statistic={statistic}
      statisticFormatter={formatter}
      isLoading={isLoading}
      compact
    />
  );
};

export default ScalarMetricCard;
