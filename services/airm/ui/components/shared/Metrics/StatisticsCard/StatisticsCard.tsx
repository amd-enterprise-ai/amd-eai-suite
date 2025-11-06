// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Card, CardBody, CardHeader, Skeleton, Tooltip } from '@heroui/react';
import { IconInfoCircle } from '@tabler/icons-react';

import { useTranslation } from 'next-i18next';

export interface StatisticsCardProps {
  title: string;
  tooltip: string;
  statistic?: number;
  upperLimit?: number;
  isLoading?: boolean;
  statisticFormatter?: (val: number) => string;
}

export const StatisticsCard: React.FC<StatisticsCardProps> = ({
  title,
  tooltip,
  statistic,
  upperLimit,
  isLoading = false,
  statisticFormatter = (val) => val.toString(),
}) => {
  const { t } = useTranslation('common');

  return (
    <Card
      className="max-w-full min-h-[128px]"
      classNames={{
        base: 'shadow-sm border-1 border-default-200 rounded-sm	dark:bg-default-100',
      }}
    >
      <CardHeader>
        <div className="flex items-center flex-grow">
          <div>{title}</div>
          <div className="ml-auto">
            <Tooltip content={tooltip} className="max-w-[300px]">
              <IconInfoCircle
                className="text-default-400 cursor-pointer"
                size={16}
              />
            </Tooltip>
          </div>
        </div>
      </CardHeader>
      <CardBody>
        {isLoading && (
          <>
            <Skeleton className="h-4 rounded-lg w-24 mb-2" />
            {upperLimit !== undefined && (
              <Skeleton className="h-3 rounded-lg w-16 mb-2" />
            )}
          </>
        )}
        {!isLoading && statistic !== undefined && (
          <>
            <div className="text-2xl font-extrabold">
              {statisticFormatter(statistic)}
            </div>
            {upperLimit !== undefined && (
              <div className="text-sm">
                {t('statistics.upperLimitPrefix')} {upperLimit}
              </div>
            )}
          </>
        )}
        {!isLoading && statistic === undefined && (
          <div className="text-xl text-default-400 font-extrabold">
            {t('statistics.noData')}
          </div>
        )}
      </CardBody>
    </Card>
  );
};
