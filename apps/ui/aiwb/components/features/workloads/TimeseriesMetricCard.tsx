// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import { StatsWithLineChart } from '@amdenterpriseai/components';
import {
  AvailableChartColorsKeys,
  TimeRange,
  TimeSeriesData,
  TimeSeriesResponse,
} from '@amdenterpriseai/types';
import { getTimeseriesMetric } from '@/lib/app/metrics';
import { useQuery } from '@tanstack/react-query';
import { useProject } from '@/contexts/ProjectContext';

export interface TimeseriesMetricConfig {
  /** Backend metric slug (e.g. 'time_to_first_token_seconds') */
  metric: string;
  /** Locale key under details.metrics (e.g. 'timeToFirstToken') */
  localeKey: string;
  /** Chart line color */
  color: AvailableChartColorsKeys;
  /** Value formatter for the chart tooltip/stat */
  dataFormatter?: (value: number | string) => string;
}

interface Props {
  config: TimeseriesMetricConfig;
  namespace: string;
  workloadId: string;
  timeRange: TimeRange;
  width?: number;
}

export const TimeseriesMetricCard: React.FC<Props> = ({
  config,
  namespace,
  workloadId,
  timeRange,
  width = 460,
}) => {
  const { t } = useTranslation('workloads');
  const { activeProject } = useProject();
  const { metric, localeKey, color, dataFormatter } = config;

  const { data, isLoading } = useQuery<TimeSeriesResponse>({
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
      getTimeseriesMetric({
        workloadId,
        namespace,
        start: timeRange.start,
        end: timeRange.end,
        metric,
      }),
  });

  const chartData: TimeSeriesData = useMemo(() => {
    if (!data?.data) return { values: [], timestamps: [], metadata: {} };

    return {
      metadata: data.data[0]?.metadata || {},
      values: data.data[0]?.values || [],
      timestamps: data.range.timestamps || [],
    };
  }, [data]);

  return (
    <StatsWithLineChart
      title={t(`details.metrics.${localeKey}.title`)}
      tooltip={t(`details.metrics.${localeKey}.description`)}
      data={chartData.values}
      dataFormatter={dataFormatter}
      width={width}
      colors={[color]}
      isLoading={isLoading}
    />
  );
};

export default TimeseriesMetricCard;
