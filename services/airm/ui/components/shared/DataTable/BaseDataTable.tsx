// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Selection,
  Skeleton,
  SortDescriptor,
  Table,
  TableBody,
  TableCell,
  TableColumn,
  TableHeader,
  TableRow,
  cn,
  getKeyValue,
} from '@heroui/react';
import React, { Key, useCallback, useMemo, useState } from 'react';

import { TFunction } from 'next-i18next';

import {
  ACTIONS_COLUMN,
  ACTIONS_COLUMN_KEY,
  getActionsColumnRenderer,
} from '@/utils/app/data-table/table-actions';

import { ActionItem, TableColumns } from '@/types/data-table/clientside-table';
import { CustomComparatorConfig } from '@/types/data-table/table-comparators';
import { PageFrameSize } from '@/types/enums/page-frame-size';
import { SortDirection } from '@/types/enums/sort-direction';

import TablePagination from './TablePagination';

interface Props<T, K extends keyof T, C> {
  data: T[];
  total: number;
  pageSize?: PageFrameSize;
  page?: number;
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
  onSortChange: (sortDescriptor: SortDescriptor) => void;
  onFrameSizeChange: (frameSize: PageFrameSize) => void;
  onPageChange: (page: number) => void;
}

const BaseDataTable = <T, K extends keyof T, C>({
  data,
  total,
  pageSize,
  page,
  className,
  columns: columnsProp,
  customRenderers,
  onSelectionChange,
  onSortChange,
  onFrameSizeChange,
  onPageChange,
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
  const t = translation;

  const [sortedBy, setSortedBy] = useState<SortDescriptor>({
    column: defaultSortByField as string,
    direction: defaultSortDirection ? defaultSortDirection : SortDirection.ASC,
  });

  const [currentPage, setCurrentPage] = useState<number>(1);
  const [frameSize, setFrameSize] = useState<PageFrameSize>(
    PageFrameSize.SMALL,
  );

  const handleSortChange = useCallback(
    (sortDescriptor: SortDescriptor) => {
      setSortedBy({ ...sortDescriptor });
      onSortChange(sortDescriptor);
    },
    [onSortChange],
  );

  const handleFrameSizeChange = useCallback(
    (frameSize: PageFrameSize) => {
      setFrameSize(frameSize);
      setCurrentPage(1);
      onFrameSizeChange(frameSize);
    },
    [onFrameSizeChange],
  );

  const handlePageChange = useCallback(
    (page: number) => {
      setCurrentPage(page);
      onPageChange(page);
    },
    [onPageChange, setCurrentPage],
  );

  const columns: TableColumns<typeof ACTIONS_COLUMN_KEY | C> = [...columnsProp];

  if (!!rowActions) {
    columns.push(ACTIONS_COLUMN);
  }

  const cellRenderer = (item: T, columnKey: Key): React.ReactNode | string => {
    if (customRenderers?.[columnKey as string]) {
      return customRenderers[columnKey as string](item);
    } else if ((columnKey as string) === ACTIONS_COLUMN_KEY && !!rowActions) {
      return getActionsColumnRenderer(rowActions, item);
    }
    return getKeyValue(item, columnKey as string);
  };

  const emptyDataPlaceholder: T[] = useMemo(
    () =>
      Array(frameSize)
        .fill(0)
        .map(
          (_, row) =>
            ({
              [idKey as string]: `row-${row}`,
            }) as T,
        ),
    [idKey, frameSize],
  );

  return (
    <div className={className}>
      <Table
        aria-label={
          t(
            `list.${translationKeyPrefix ? `${translationKeyPrefix}.` : ''}table.ariaLabel`,
          ) || ''
        }
        shadow="none"
        selectedKeys={selectedKeys}
        selectionMode={isSelectable ? 'multiple' : 'none'}
        onRowAction={onRowPressed && ((id) => onRowPressed(id as string))}
        onSelectionChange={onSelectionChange}
        sortDescriptor={sortedBy}
        onSortChange={handleSortChange}
        classNames={{
          wrapper: 'px-0 py-0',
          tr: cn({
            'cursor-pointer': !!onRowPressed || isSelectable,
            '[&:hover>td]:before:opacity-70': !isLoading,
            '[&:last-child>td]:border-b-0': true,
            '[&:first-child>td:first-child]:before:rounded-ss-xl [&:first-child>td:last-child]:before:rounded-se-xl': true,
            '[&:last-child>td:first-child]:before:rounded-es-xl [&:last-child>td:last-child]:before:rounded-ee-xl': true,
          }),
          td: cn({
            'border-b border-default-100': true,
            'before:-z-[1]': true,
            'before:bg-default-100': true,
            '[&:first-child]:before:rounded-s-none [&:last-child]:before:rounded-e-none': true,
          }),
        }}
        bottomContent={
          total > PageFrameSize.SMALL &&
          !isLoading && (
            <TablePagination
              onFrameSizeChange={handleFrameSizeChange}
              onPageChange={handlePageChange}
              currentPage={page ?? currentPage}
              frameSize={pageSize ?? frameSize}
              translationKeyPrefix={translationKeyPrefix}
              totalItems={total}
              translation={translation}
            />
          )
        }
      >
        <TableHeader columns={columns}>
          {(column) => (
            <TableColumn
              className={`align-top ${column.hasDescription ? 'h-14' : ''} ${column.className || ''}`}
              key={column.key as string}
              width={column.width}
              maxWidth={column.maxWidth}
              minWidth={column.minWidth}
              allowsSorting={column.sortable}
            >
              {column.key ? (
                <div className="inline-flex flex-col mt-3">
                  <div className="uppercase">
                    {t(
                      `list.${translationKeyPrefix ? `${translationKeyPrefix}.` : ''}headers.${column.key as string}.title`,
                    )}
                  </div>
                  {!!column.hasDescription && (
                    <div className="uppercase text-default-500 text-xs">
                      {t(
                        `list.${translationKeyPrefix ? `${translationKeyPrefix}.` : ''}headers.${column.key as string}.description`,
                      )}
                    </div>
                  )}
                </div>
              ) : null}
            </TableColumn>
          )}
        </TableHeader>
        <TableBody
          emptyContent={t(
            `list.${translationKeyPrefix ? `${translationKeyPrefix}.` : ''}empty.description`,
          )}
          items={isLoading ? emptyDataPlaceholder : data}
          isLoading={isFetching}
        >
          {(item) => (
            <TableRow key={`${item[idKey]}`}>
              {(columnKey) => (
                <TableCell>
                  {isLoading ? (
                    <Skeleton
                      key={`skeleton-${String(columnKey)}`}
                      className="w-3/5 rounded-lg"
                    >
                      <div className="h-4 w-3/5 rounded-lg bg-default-200" />
                    </Skeleton>
                  ) : (
                    cellRenderer(item, columnKey)
                  )}
                </TableCell>
              )}
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
};

export default BaseDataTable;
