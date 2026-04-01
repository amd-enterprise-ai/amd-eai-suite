// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useTranslation } from 'next-i18next';

import type {
  TimeRangePeriod,
  TimeSeriesAllocationData,
} from '@amdenterpriseai/types';

import { StatsWithLineChart } from '@amdenterpriseai/components';
import { useGPUMetrics } from '@/hooks/useGPUMetrics';

// Constants
const CHART_GUIDE_COLOR = 'gray' as const;
const DEFAULT_CHART_WIDTH = 460;

// Type definitions
type DashboardProps = {
  data: TimeSeriesAllocationData;
  isLoading?: boolean;
  width?: number;
  workloadId?: never;
  namespace?: never;
  timePeriod?: never;
};

type WorkloadProps = {
  data?: never;
  workloadId: string;
  namespace: string;
  timePeriod: TimeRangePeriod;
  isLoading?: boolean;
  width?: number;
};

type BaseProps = DashboardProps | WorkloadProps;

type ChartColor =
  | 'blue'
  | 'cyan'
  | 'darkgray'
  | 'fuchsia'
  | 'gray'
  | 'green'
  | 'lime'
  | 'pink'
  | 'red'
  | 'violet'
  | 'emerald'
  | 'amber';

export interface GPUUsageCardConfig {
  metricName: string;
  chartColor: ChartColor;
  titleKey: string;
  tooltipKey: string;
  upperLimitUnallocatedKey: string;
  upperLimitKey: string;
  dataFormatter: (value: number | null) => string;
}

type Props = BaseProps & {
  config: GPUUsageCardConfig;
};

/**
 * Base component for displaying GPU usage metrics with a line chart.
 * Supports both dashboard mode (static data) and workload mode (fetched data).
 *
 * @param props - Component props (DashboardProps or WorkloadProps)
 * @param props.config - Configuration object for the specific GPU metric
 * @returns Rendered stats card with line chart
 */
export const BaseGPUUsageCard: React.FC<Props> = (props) => {
  const { config } = props;
  const { t } = useTranslation('projects');

  // Determine mode and prepare params for the hook
  const isWorkload = 'workloadId' in props && props.workloadId != null;

  const metricsConfig = isWorkload
    ? {
        type: 'workload' as const,
        params: {
          workloadId: (props as WorkloadProps).workloadId,
          namespace: (props as WorkloadProps).namespace,
          timePeriod: (props as WorkloadProps).timePeriod,
          metricName: config.metricName,
        },
      }
    : {
        type: 'dashboard' as const,
        params: {
          data: (props as DashboardProps).data,
        },
      };

  // Fetch and transform data
  const { chartData, isLoading } = useGPUMetrics(
    metricsConfig,
    (props as DashboardProps).isLoading,
  );

  const width =
    ('width' in props ? props.width : undefined) ?? DEFAULT_CHART_WIDTH;

  // Determine if denominator data is available
  const hasDenominator = chartData.denominator.length > 0;

  return (
    <StatsWithLineChart
      title={t(config.titleKey)}
      tooltip={t(config.tooltipKey)}
      data={chartData.numerator}
      dataFormatter={(value) => config.dataFormatter(Number(value))}
      upperLimitData={hasDenominator ? chartData.denominator : undefined}
      upperLimitFormatter={
        hasDenominator
          ? (value) =>
              value === null || value === 0
                ? t(config.upperLimitUnallocatedKey)
                : t(config.upperLimitKey, {
                    num: config.dataFormatter(Number(value)),
                  })
          : undefined
      }
      width={width}
      colors={
        hasDenominator
          ? [CHART_GUIDE_COLOR, config.chartColor]
          : [config.chartColor]
      }
      isLoading={isLoading}
    />
  );
};

export default BaseGPUUsageCard;
