// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useTranslation } from 'next-i18next';

import { displayTimestamp } from '@/utils/app/strings';

import RefreshButton from '../Filters/RefreshButton';

interface Props {
  onRefresh: () => void;
  lastFetchedTimestamp?: Date;
  isRefreshing?: boolean;
  compact?: boolean;
  reversed?: boolean;
}

export const DataRefresher: React.FC<Props> = ({
  onRefresh,
  lastFetchedTimestamp,
  isRefreshing = false,
  compact = false,
  reversed = false,
}) => {
  const { t } = useTranslation('common');

  return (
    <div className={`flex items-center ${reversed ? 'flex-row-reverse' : ''}`}>
      {lastFetchedTimestamp ? (
        <span className="text-sm text-default-500 dark:text-default-400 mx-4">
          {t(`data.lastUpdated`, {
            timestamp: displayTimestamp(lastFetchedTimestamp),
          })}
        </span>
      ) : null}

      <RefreshButton
        compact={compact}
        isLoading={isRefreshing}
        onPress={onRefresh}
      />
    </div>
  );
};

export default DataRefresher;
