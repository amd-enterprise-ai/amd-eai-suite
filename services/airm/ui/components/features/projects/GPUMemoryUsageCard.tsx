// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useTranslation } from 'next-i18next';

import { displayHumanReadableMegaBytes } from '@/utils/app/strings';

import { TimeSeriesAllocationData } from '@/types/metrics';

import { StatsWithLineChart } from '@/components/shared/Metrics/StatsWithLineChartCard';

interface Props {
  data: TimeSeriesAllocationData;
  isLoading?: boolean;
  width?: number;
}

const CHART_COLOR = 'cyan';
const CHART_GUIDE_COLOR = 'gray';

export const GPUMemoryUsageCard: React.FC<Props> = ({
  data,
  isLoading = false,
  width = 460,
}) => {
  const { t } = useTranslation('projects');

  return (
    <StatsWithLineChart
      title={t('dashboard.overview.vramDeviceUsage.title')}
      tooltip={t('dashboard.overview.vramDeviceUsage.description')}
      data={data.numerator}
      dataFormatter={(value) => displayHumanReadableMegaBytes(Number(value))}
      upperLimitData={data.denominator}
      colors={[CHART_GUIDE_COLOR, CHART_COLOR]}
      width={width}
      upperLimitFormatter={(value) =>
        value === null || value === 0
          ? t('dashboard.overview.vramDeviceUsage.upperLimitUnallocated')
          : t('dashboard.overview.vramDeviceUsage.upperLimit', {
              num: displayHumanReadableMegaBytes(Number(value)),
            })
      }
      isLoading={isLoading}
    />
  );
};

export default GPUMemoryUsageCard;
