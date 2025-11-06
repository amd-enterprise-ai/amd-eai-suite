// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Tab, Tabs } from '@heroui/react';
import { useCallback } from 'react';

import { useTranslation } from 'next-i18next';

import { getCurrentTimeRange } from '@/utils/app/time-range';

import { TimeRangePeriod } from '@/types/enums/metrics';
import { TimeRange } from '@/types/metrics';

import { DataRefresher } from '../../DataRefresher';

interface ChartTimeSelectorProps {
  onTimeRangeChange: (
    timerangePeriod: TimeRangePeriod,
    timeRange: TimeRange,
  ) => void;
  onChartsRefresh: () => void;
  isFetching?: boolean;
  lastFetchedTimestamp?: Date;
  initialTimePeriod?: TimeRangePeriod;
  translationPrefix?: string;
}

const filterByRangeTabs = [
  { id: TimeRangePeriod['1H'] },
  { id: TimeRangePeriod['24H'] },
  { id: TimeRangePeriod['7D'] },
];

export const ChartTimeSelector: React.FC<ChartTimeSelectorProps> = ({
  onTimeRangeChange,
  onChartsRefresh,
  isFetching = false,
  lastFetchedTimestamp,
  initialTimePeriod = TimeRangePeriod['1H'],
  translationPrefix = 'timeRange',
}) => {
  const { t } = useTranslation('common');

  const handleTimeBoundChange = useCallback(
    (timePeriod: React.Key) => {
      const newTimeRange = getCurrentTimeRange(timePeriod as TimeRangePeriod);
      onTimeRangeChange(timePeriod as TimeRangePeriod, newTimeRange);
    },
    [onTimeRangeChange],
  );

  return (
    <div className="flex gap-3 items-center justify-end">
      <DataRefresher
        onRefresh={onChartsRefresh}
        lastFetchedTimestamp={lastFetchedTimestamp}
        isRefreshing={isFetching}
      />
      <Tabs
        isDisabled={isFetching}
        aria-label={t(`${translationPrefix}.description`) || ''}
        items={filterByRangeTabs}
        placement="top"
        classNames={{
          base: 'justify-end w-full',
        }}
        defaultSelectedKey={initialTimePeriod}
        onSelectionChange={handleTimeBoundChange}
      >
        {(item) => (
          <Tab
            key={item.id}
            title={t(`${translationPrefix}.range.${item.id}`)}
          ></Tab>
        )}
      </Tabs>
    </div>
  );
};

export default ChartTimeSelector;
