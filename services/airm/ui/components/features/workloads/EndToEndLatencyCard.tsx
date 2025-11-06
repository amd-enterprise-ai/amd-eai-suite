// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useTranslation } from 'next-i18next';

import { TimeRange, TimeSeriesData, TimeSeriesResponse } from '@/types/metrics';

import { StatsWithLineChart } from '@/components/shared/Metrics/StatsWithLineChartCard';
import { formatSeconds } from '@/utils/app/strings';
import { Workload } from '@/types/workloads';
import { getEndToEndLatency } from '@/services/app/workloads';
import { WorkloadType, WorkloadStatus } from '@/types/enums/workloads';
import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { useProject } from '@/contexts/ProjectContext';
import { InferenceMetricsColors } from '@/types/enums/inference-metrics';

interface Props {
  workload: Workload;
  timeRange: TimeRange;
  width?: number;
}

const CHART_COLOR = InferenceMetricsColors.END_TO_END_LATENCY;

export const EndToEndLatencyCard: React.FC<Props> = ({
  workload,
  timeRange,
  width = 460,
}) => {
  const { t } = useTranslation('workloads');
  const { activeProject } = useProject();

  const { data: endToEndLatencyData, isLoading: isEndToEndLatencyLoading } =
    useQuery<TimeSeriesResponse>({
      queryKey: [
        'project',
        activeProject,
        'workload',
        workload.id,
        'metrics',
        'endToEndLatency',
        {
          start: timeRange.start.toISOString(),
          end: timeRange.end.toISOString(),
        },
      ],
      queryFn: () =>
        getEndToEndLatency(
          workload.id as string,
          timeRange.start,
          timeRange.end,
        ),
      enabled:
        !!workload.id &&
        workload?.type === WorkloadType.INFERENCE &&
        workload?.status === WorkloadStatus.RUNNING,
    });

  const endToEndLatencyChartData: TimeSeriesData = useMemo(() => {
    if (!endToEndLatencyData?.data)
      return { values: [], timestamps: [], metadata: {} };

    return {
      metadata: endToEndLatencyData.data[0]?.metadata || {},
      values: endToEndLatencyData.data[0]?.values || [],
      timestamps: endToEndLatencyData.range.timestamps || [],
    };
  }, [endToEndLatencyData]);

  return (
    <StatsWithLineChart
      title={t('details.metrics.endToEndLatency.title')}
      tooltip={t('details.metrics.endToEndLatency.description')}
      data={endToEndLatencyChartData.values}
      dataFormatter={formatSeconds}
      width={width}
      colors={[CHART_COLOR]}
      isLoading={isEndToEndLatencyLoading}
    />
  );
};

export default EndToEndLatencyCard;
