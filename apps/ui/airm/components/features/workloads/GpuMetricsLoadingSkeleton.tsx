// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Skeleton } from '@heroui/react';
import { useTranslation } from 'next-i18next';

import { AvailableChartColorsKeys } from '@amdenterpriseai/types';

import { StatsWithLineChart } from '@amdenterpriseai/components';

const PLACEHOLDER_ROWS = [1, 2];

export const GpuMetricsLoadingSkeleton: React.FC = () => {
  const { t } = useTranslation('workloads');

  return (
    <div className="flex flex-col gap-6">
      {PLACEHOLDER_ROWS.map((row) => (
        <div key={row} className="flex flex-col gap-3">
          <Skeleton className="h-4 w-48 rounded" />
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <StatsWithLineChart
              title={t('details.fields.memoryUtilization')}
              tooltip={t('details.fields.memoryUtilizationTooltip')}
              data={[]}
              dataFormatter={(v) => `${Number(v).toFixed(0)}%`}
              showValueAsPercentage={false}
              isLoading
              colors={['violet' as AvailableChartColorsKeys]}
              showYAxis
            />
            <StatsWithLineChart
              title={t('details.fields.junctionTemperature')}
              tooltip={t('details.fields.junctionTemperatureTooltip')}
              data={[]}
              dataFormatter={(v) => `${Number(v).toFixed(1)}°C`}
              isLoading
              colors={['amber' as AvailableChartColorsKeys]}
              showYAxis
            />
            <StatsWithLineChart
              title={t('details.fields.gpuPowerUsage')}
              tooltip={t('details.fields.gpuPowerUsageTooltip')}
              data={[]}
              dataFormatter={(v) => `${Number(v).toFixed(0)}W`}
              isLoading
              colors={['cyan' as AvailableChartColorsKeys]}
              showYAxis
            />
          </div>
        </div>
      ))}
    </div>
  );
};
