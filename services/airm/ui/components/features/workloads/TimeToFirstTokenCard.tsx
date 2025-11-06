// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useTranslation } from 'next-i18next';

import { TimeRange, TimeSeriesData, TimeSeriesResponse } from '@/types/metrics';

import { StatsWithLineChart } from '@/components/shared/Metrics/StatsWithLineChartCard';
import { formatSeconds } from '@/utils/app/strings';
import { useQuery } from '@tanstack/react-query';
import { getTimeToFirstToken } from '@/services/app/workloads';
import { Workload } from '@/types/workloads';
import { WorkloadStatus, WorkloadType } from '@/types/enums/workloads';
import { useMemo } from 'react';
import { useProject } from '@/contexts/ProjectContext';
import { InferenceMetricsColors } from '@/types/enums/inference-metrics';

interface Props {
  workload: Workload;
  timeRange: TimeRange;
  width?: number;
}

const CHART_COLOR = InferenceMetricsColors.TIME_TO_FIRST_TOKEN;

export const TimeToFirstTokenCard: React.FC<Props> = ({
  workload,
  timeRange,
  width = 460,
}) => {
  const { t } = useTranslation('workloads');
  const { activeProject } = useProject();

  const { data: timeToFirstTokenData, isLoading: isTimeToFirstTokenLoading } =
    useQuery<TimeSeriesResponse>({
      queryKey: [
        'project',
        activeProject,
        'workload',
        workload.id,
        'metrics',
        'timeToFirstToken',
        {
          start: timeRange.start.toISOString(),
          end: timeRange.end.toISOString(),
        },
      ],
      queryFn: () =>
        getTimeToFirstToken(
          workload.id as string,
          timeRange.start,
          timeRange.end,
        ),
      enabled:
        !!workload.id &&
        workload.type === WorkloadType.INFERENCE &&
        workload.status === WorkloadStatus.RUNNING,
    });

  const timeToFirstTokenChartData: TimeSeriesData = useMemo(() => {
    if (!timeToFirstTokenData?.data)
      return { values: [], timestamps: [], metadata: {} };

    return {
      metadata: timeToFirstTokenData.data[0]?.metadata || {},
      values: timeToFirstTokenData.data[0]?.values || [],
      timestamps: timeToFirstTokenData.range.timestamps || [],
    };
  }, [timeToFirstTokenData]);

  return (
    <StatsWithLineChart
      title={t('details.metrics.timeToFirstToken.title')}
      tooltip={t('details.metrics.timeToFirstToken.description')}
      data={timeToFirstTokenChartData.values}
      dataFormatter={formatSeconds}
      width={width}
      colors={[CHART_COLOR]}
      isLoading={isTimeToFirstTokenLoading}
    />
  );
};

export default TimeToFirstTokenCard;
