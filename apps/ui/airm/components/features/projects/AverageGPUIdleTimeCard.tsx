// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import { formatDurationFromSeconds } from '@amdenterpriseai/utils/app';

import { MetricScalarResponse } from '@amdenterpriseai/types';

import { StatisticsCard } from '@amdenterpriseai/components';

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
