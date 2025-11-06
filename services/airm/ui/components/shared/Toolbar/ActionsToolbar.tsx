// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ReactNode } from 'react';
import { FilterFieldMapping, FilterValueMap } from '@/types/filters';
import { DataFilter } from '@/components/shared/Filters';
import { Toolbar } from '@/components/layouts/ToolbarLayout';
import RefreshButton from '@/components/shared/Filters/RefreshButton';

interface Props {
  filterConfig: FilterFieldMapping;
  onFilterChange: (filters: FilterValueMap) => void;
  onRefresh?: () => void;
  isRefreshing?: boolean;
  updatedTimestamp?: number;
  extraContent?: ReactNode;
  endContent?: ReactNode;
}

export const ActionsToolbar = ({
  filterConfig,
  isRefreshing,
  onFilterChange,
  onRefresh,
  extraContent,
  endContent,
  updatedTimestamp,
}: Props) => {
  return (
    <Toolbar>
      <div
        className={`flex w-full lg:w-[fit-content] gap-3 items-center flex-wrap order-2 lg:order-1 ${endContent == undefined ? 'flex-1' : ''}`}
      >
        {onRefresh ? (
          <RefreshButton
            compact
            isLoading={isRefreshing}
            onPress={onRefresh}
            lastFetchedTimestamp={updatedTimestamp}
          />
        ) : null}
        <DataFilter filters={filterConfig} onFilterChange={onFilterChange} />
        {extraContent}
      </div>
      {endContent != undefined ? (
        <>
          <div className="flex items-center gap-3 sm:justify-start justify-end ml-auto lg:ml-0 order-1 lg:order-2">
            {endContent}
          </div>
          <div className="w-full border-b border-gray-300 lg:hidden order-1 lg:order-2"></div>
        </>
      ) : null}
    </Toolbar>
  );
};

export default ActionsToolbar;
