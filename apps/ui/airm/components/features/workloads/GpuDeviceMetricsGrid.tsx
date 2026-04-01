// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Button } from '@heroui/react';
import { useTranslation } from 'next-i18next';
import { useRouter } from 'next/router';

import { AvailableChartColorsKeys } from '@amdenterpriseai/types';
import { WorkloadGpuDeviceSnapshot } from '@/types/workloads';
import { ClusterNode } from '@amdenterpriseai/types';
import { TimeSeriesDataPoint } from '@amdenterpriseai/types';

import { StatsWithLineChart } from '@amdenterpriseai/components';

interface GpuDeviceMetricsGridProps {
  devices: WorkloadGpuDeviceSnapshot[];
  nodesByHostname: Map<string, ClusterNode>;
  clusterId?: string;
  isFetching: boolean;
}

const toTimeSeriesDataPoints = (
  series: { time: string; value: number }[] = [],
): TimeSeriesDataPoint[] =>
  series.map((p) => ({ timestamp: p.time, value: p.value }));

export const GpuDeviceMetricsGrid: React.FC<GpuDeviceMetricsGridProps> = ({
  devices,
  nodesByHostname,
  clusterId,
  isFetching,
}) => {
  const { t } = useTranslation('workloads');
  const router = useRouter();

  return (
    <div className="flex flex-col gap-6">
      {devices.map((device) => {
        const deviceName = device.displayLabel || `gpu-device-${device.gpuId}`;

        const matchedNode = device.hostname
          ? nodesByHostname.get(device.hostname)
          : undefined;

        return (
          <div key={device.gpuUuid} className="flex flex-col gap-3">
            <div className="flex items-center justify-between gap-2">
              <h4 className="text-sm font-medium text-default-600 min-w-0 truncate">
                {deviceName}
                {device.hostname && (
                  <span className="text-default-400 font-normal">
                    {' '}
                    ({device.hostname})
                  </span>
                )}
              </h4>
              {matchedNode && (
                <Button
                  variant="light"
                  size="sm"
                  onPress={() =>
                    router.push(
                      `/clusters/${clusterId}/nodes/${matchedNode.id}`,
                    )
                  }
                  className="text-primary shrink-0"
                >
                  {t('details.fields.viewAllMetrics')}
                </Button>
              )}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <StatsWithLineChart
                title={t('details.fields.memoryUtilization')}
                tooltip={t('details.fields.memoryUtilizationTooltip')}
                data={toTimeSeriesDataPoints(device.vramUtilizationSeries)}
                dataFormatter={(v) => `${Number(v).toFixed(0)}%`}
                showValueAsPercentage
                isLoading={isFetching}
                colors={['violet' as AvailableChartColorsKeys]}
                showYAxis
              />
              <StatsWithLineChart
                title={t('details.fields.junctionTemperature')}
                tooltip={t('details.fields.junctionTemperatureTooltip')}
                data={toTimeSeriesDataPoints(device.junctionTemperatureSeries)}
                dataFormatter={(v) => `${Number(v).toFixed(1)}°C`}
                isLoading={isFetching}
                colors={['amber' as AvailableChartColorsKeys]}
                showYAxis
              />
              <StatsWithLineChart
                title={t('details.fields.gpuPowerUsage')}
                tooltip={t('details.fields.gpuPowerUsageTooltip')}
                data={toTimeSeriesDataPoints(device.powerUsageSeries)}
                dataFormatter={(v) => `${Number(v).toFixed(0)}W`}
                isLoading={isFetching}
                colors={['cyan' as AvailableChartColorsKeys]}
                showYAxis
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};
