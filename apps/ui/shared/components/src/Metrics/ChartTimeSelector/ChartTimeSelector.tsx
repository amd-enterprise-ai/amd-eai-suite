// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Tab, Tabs } from '@heroui/react';
import { useCallback } from 'react';

import { useTranslation } from 'next-i18next';

import { getCurrentTimeRange } from '@amdenterpriseai/utils/app';

import {
  TimeRangePeriod,
  DEFAULT_CHART_TIME_PERIODS,
} from '@amdenterpriseai/types';
import { TimeRange } from '@amdenterpriseai/types';

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
  /** When set, overrides the default periods (1H, 24H, 7D). e.g. [15M, 30M, 1H, 24H, 7D] for inference metrics. */
  periods?: TimeRangePeriod[];
}

export const ChartTimeSelector: React.FC<ChartTimeSelectorProps> = ({
  onTimeRangeChange,
  onChartsRefresh,
  isFetching = false,
  lastFetchedTimestamp,
  initialTimePeriod = TimeRangePeriod['1H'],
  translationPrefix = 'timeRange',
  periods = DEFAULT_CHART_TIME_PERIODS,
}) => {
  const { t } = useTranslation('common');

  const tabItems = periods.map((id) => ({ id }));

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
        items={tabItems}
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
