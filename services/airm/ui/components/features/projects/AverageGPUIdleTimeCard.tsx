// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import { formatDurationFromSeconds } from '@/utils/app/strings';

import { MetricScalarResponse } from '@/types/metrics';

import { StatisticsCard } from '@/components/shared/Metrics/StatisticsCard';

interface Props {
  data: MetricScalarResponse | undefined;
  isLoading?: boolean;
}

export const AverageGPUIdleTimeCard: React.FC<Props> = ({
  isLoading = false,
  data,
}) => {
  const { t } = useTranslation('projects');

  const avgGPUIdleTime = useMemo(() => {
    return data?.data ?? 0;
  }, [data]);

  return (
    <StatisticsCard
      title={t('dashboard.overview.gpuIdleTimeAvg.title')}
      tooltip={t('dashboard.overview.gpuIdleTimeAvg.description')}
      statistic={avgGPUIdleTime}
      statisticFormatter={formatDurationFromSeconds}
      isLoading={isLoading}
    />
  );
};

export default AverageGPUIdleTimeCard;
