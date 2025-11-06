// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useTranslation } from 'next-i18next';

import { TimeSeriesAllocationData } from '@/types/metrics';

import { StatsWithLineChart } from '@/components/shared/Metrics/StatsWithLineChartCard';

interface Props {
  data: TimeSeriesAllocationData;
  isLoading?: boolean;
  width?: number;
}

const CHART_COLOR = 'fuchsia';
const CHART_GUIDE_COLOR = 'gray';

export const GPUDeviceUsageCard: React.FC<Props> = ({
  data,
  width = 460,
  isLoading,
}) => {
  const { t } = useTranslation('projects');

  return (
    <StatsWithLineChart
      title={t('dashboard.overview.gpuDeviceUsage.title')}
      tooltip={t('dashboard.overview.gpuDeviceUsage.description')}
      data={data.numerator}
      dataFormatter={(value) => Number(value).toFixed(0)}
      upperLimitData={data.denominator}
      upperLimitFormatter={(value) =>
        value === null || value === 0
          ? t('dashboard.overview.gpuDeviceUsage.upperLimitUnallocated')
          : t('dashboard.overview.gpuDeviceUsage.upperLimit', {
              num: Number(value).toFixed(0),
            })
      }
      width={width}
      colors={[CHART_GUIDE_COLOR, CHART_COLOR]}
      isLoading={isLoading}
    />
  );
};

export default GPUDeviceUsageCard;
