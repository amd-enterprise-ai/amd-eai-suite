// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Selection, SortDescriptor } from '@heroui/react';
import React, { useCallback, useMemo, useState } from 'react';

import { TFunction } from 'next-i18next';

import { defaultComparator } from '@/utils/app/data-table';

import { ActionItem, TableColumns } from '@/types/data-table/clientside-table';
import { CustomComparatorConfig } from '@/types/data-table/table-comparators';
import { PageFrameSize } from '@/types/enums/page-frame-size';
import { SortDirection } from '@/types/enums/sort-direction';

import BaseDataTable from './BaseDataTable';

interface Props<T, K extends keyof T, C> {
  data: T[];
  columns: TableColumns<C>;
  customComparator?: CustomComparatorConfig<T, K>;
  className?: string;
  defaultSortByField: C;
  defaultSortDirection?: SortDirection;
  translation: TFunction;
  translationKeyPrefix?: string;
  idKey: keyof T;
  isLoading?: boolean;
  isFetching?: boolean;
  selectedKeys?: Selection;
  isSelectable?: boolean;
  onSelectionChange?: (keys: Selection) => void;
  customRenderers?: Record<string, (item: T) => React.ReactNode | string>;
  onRowPressed?: (id: string) => void;
  rowActions?: ActionItem<T>[] | ((item: T) => ActionItem<T>[]);
}

export const ClientSideDataTable = <T, K extends keyof T, C>({
  data,
  className,
  columns,
  customRenderers,
  customComparator,
  onSelectionChange,
  selectedKeys,
  idKey,
  defaultSortByField,
  defaultSortDirection,
  isFetching,
  isLoading,
  isSelectable,
  translation,
  translationKeyPrefix,
  onRowPressed,
  rowActions,
}: Props<T, K, C>) => {
  const [sortedBy, setSortedBy] = useState<SortDescriptor>({
    column: defaultSortByField as string,
    direction: defaultSortDirection ? defaultSortDirection : SortDirection.ASC,
  });

  const [currentPage, setCurrentPage] = useState<number>(1);
  const [frameSize, setFrameSize] = useState<PageFrameSize>(
    PageFrameSize.SMALL,
  );

  const [prevDataLength, setPrevDataLength] = useState<number>();
  if (prevDataLength !== data.length) {
    setPrevDataLength(data.length);
    setCurrentPage(1);
  }

  const sortedData = useMemo(() => {
    const column = sortedBy.column as C;
    const sorted = [...data].sort(
      customComparator?.[column] || defaultComparator(column as string),
    );
    if (sortedBy.direction === SortDirection.DESC) {
      sorted.reverse();
    }
    return sorted;
  }, [data, customComparator, sortedBy.direction, sortedBy.column]);

  const dataFrame = useMemo(() => {
    const currentIdx = (currentPage - 1) * frameSize;
    return sortedData.slice(currentIdx, currentIdx + frameSize);
  }, [currentPage, sortedData, frameSize]);

  const handleSortChange = useCallback((sortDescriptor: SortDescriptor) => {
    setSortedBy({ ...sortDescriptor });
  }, []);

  const handleFrameSizeChange = (frameSize: PageFrameSize) => {
    setFrameSize(frameSize);
    setCurrentPage(1);
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  return (
    <BaseDataTable
      data={dataFrame}
      total={data.length}
      className={className}
      columns={columns}
      customRenderers={customRenderers}
      onSelectionChange={onSelectionChange}
      selectedKeys={selectedKeys}
      idKey={idKey}
      defaultSortByField={defaultSortByField}
      defaultSortDirection={defaultSortDirection}
      isFetching={isFetching}
      isLoading={isLoading}
      isSelectable={isSelectable}
      translation={translation}
      translationKeyPrefix={translationKeyPrefix}
      onRowPressed={onRowPressed}
      rowActions={rowActions}
      onSortChange={handleSortChange}
      onFrameSizeChange={handleFrameSizeChange}
      onPageChange={handlePageChange}
    />
  );
};

export default ClientSideDataTable;
