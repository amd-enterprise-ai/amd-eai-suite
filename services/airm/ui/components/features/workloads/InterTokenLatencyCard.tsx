// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useTranslation } from 'next-i18next';

import { TimeRange, TimeSeriesData, TimeSeriesResponse } from '@/types/metrics';

import { StatsWithLineChart } from '@/components/shared/Metrics/StatsWithLineChartCard';
import { formatSeconds } from '@/utils/app/strings';
import { Workload } from '@/types/workloads';
import { useQuery } from '@tanstack/react-query';
import { getInterTokenLatency } from '@/services/app/workloads';
import { WorkloadStatus, WorkloadType } from '@/types/enums/workloads';
import { useMemo } from 'react';
import { useProject } from '@/contexts/ProjectContext';
import { InferenceMetricsColors } from '@/types/enums/inference-metrics';

interface Props {
  workload: Workload;
  timeRange: TimeRange;
  width?: number;
}

const CHART_COLOR = InferenceMetricsColors.INTER_TOKEN_LATENCY;

export const InterTokenLatencyCard: React.FC<Props> = ({
  workload,
  timeRange,
  width = 460,
}) => {
  const { t } = useTranslation('workloads');
  const { activeProject } = useProject();

  const { data: interTokenLatencyData, isLoading: isInterTokenLatencyLoading } =
    useQuery<TimeSeriesResponse>({
      queryKey: [
        'project',
        activeProject,
        'workload',
        workload.id,
        'metrics',
        'interTokenLatency',
        {
          start: timeRange.start.toISOString(),
          end: timeRange.end.toISOString(),
        },
      ],
      queryFn: () =>
        getInterTokenLatency(
          workload.id as string,
          timeRange.start,
          timeRange.end,
        ),
      enabled:
        !!workload.id &&
        workload.type === WorkloadType.INFERENCE &&
        workload.status === WorkloadStatus.RUNNING,
    });

  const interTokenLatencyChartData: TimeSeriesData = useMemo(() => {
    if (!interTokenLatencyData?.data)
      return { values: [], timestamps: [], metadata: {} };

    return {
      metadata: interTokenLatencyData.data[0]?.metadata || {},
      values: interTokenLatencyData.data[0]?.values || [],
      timestamps: interTokenLatencyData.range.timestamps || [],
    };
  }, [interTokenLatencyData]);

  return (
    <StatsWithLineChart
      title={t('details.metrics.interTokenLatency.title')}
      tooltip={t('details.metrics.interTokenLatency.description')}
      data={interTokenLatencyChartData.values}
      dataFormatter={formatSeconds}
      width={width}
      colors={[CHART_COLOR]}
      isLoading={isInterTokenLatencyLoading}
    />
  );
};

export default InterTokenLatencyCard;
