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
  compact?: boolean;
  /** Override the CSS class on the value element, e.g. when the value is expected to be long text */
  valueClassName?: string;
}

export const StatisticsCard: React.FC<StatisticsCardProps> = ({
  title,
  tooltip,
  statistic,
  upperLimit,
  isLoading = false,
  statisticFormatter = (val) => val.toString(),
  compact = false,
  valueClassName,
}) => {
  const { t } = useTranslation('common');
  const formattedStatistic =
    statistic !== undefined ? statisticFormatter(statistic) : undefined;

  return (
    <Card
      className={compact ? 'max-w-full h-full' : 'max-w-full min-h-[128px]'}
      classNames={{
        base: 'shadow-sm border-1 border-default-200 rounded-sm	dark:bg-default-100',
      }}
    >
      <CardHeader className={compact ? 'py-2 px-4' : undefined}>
        <div className="flex items-center flex-grow">
          <div className={compact ? 'text-sm' : undefined}>{title}</div>
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
      <CardBody className={compact ? 'py-2 pt-0 px-4' : undefined}>
        {isLoading && (
          <>
            <Skeleton
              className={
                compact
                  ? 'h-3 rounded-lg w-20 mb-1'
                  : 'h-4 rounded-lg w-24 mb-2'
              }
            />
            {upperLimit !== undefined && (
              <Skeleton className="h-3 rounded-lg w-16 mb-2" />
            )}
          </>
        )}
        {!isLoading && statistic !== undefined && (
          <>
            <div
              className={
                valueClassName ??
                (compact ? 'text-xl font-extrabold' : 'text-2xl font-extrabold')
              }
              title={formattedStatistic}
            >
              {formattedStatistic}
            </div>
            {upperLimit !== undefined && (
              <div className="text-sm">
                {t('statistics.upperLimitPrefix')} {upperLimit}
              </div>
            )}
          </>
        )}
        {!isLoading && statistic === undefined && (
          <div
            className={
              compact
                ? 'text-lg text-default-400 font-extrabold'
                : 'text-xl text-default-400 font-extrabold'
            }
          >
            {t('statistics.noData')}
          </div>
        )}
      </CardBody>
    </Card>
  );
};
