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
} from '../Dropdown/table-actions';

import { ActionItem, TableColumns } from '@amdenterpriseai/types';
import { CustomComparatorConfig } from '@amdenterpriseai/types';
import { PageFrameSize } from '@amdenterpriseai/types';
import { SortDirection } from '@amdenterpriseai/types';

import TablePagination from './TablePagination';

export type TableVariant = 'default' | 'transparent';

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
  isRowDisabled?: (item: T) => boolean;
  onSortChange: (sortDescriptor: SortDescriptor) => void;
  onFrameSizeChange: (frameSize: PageFrameSize) => void;
  onPageChange: (page: number) => void;
  tableVariant?: TableVariant;
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
  isRowDisabled,
  tableVariant = 'default',
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

  // Compute disabledKeys from isRowDisabled if provided
  const computedDisabledKeys = useMemo(() => {
    if (isRowDisabled) {
      const disabled = data
        .filter((item) => isRowDisabled(item))
        .map((item) => item[idKey] as string | number);
      return disabled.length > 0 ? new Set(disabled) : undefined;
    }
    return undefined;
  }, [isRowDisabled, data, idKey]);

  const columns: TableColumns<typeof ACTIONS_COLUMN_KEY | C> = [...columnsProp];

  if (rowActions) {
    columns.push(ACTIONS_COLUMN);
  }

  const cellRenderer = (item: T, columnKey: Key): React.ReactNode | string => {
    if (customRenderers?.[columnKey as string]) {
      return customRenderers[columnKey as string](item);
    } else if ((columnKey as string) === ACTIONS_COLUMN_KEY && !!rowActions) {
      const rowDisabled = isRowDisabled
        ? isRowDisabled(item)
        : (computedDisabledKeys?.has(item[idKey] as string | number) ?? false);
      return getActionsColumnRenderer(rowActions, item, rowDisabled);
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
        disabledKeys={computedDisabledKeys}
        selectionMode={isSelectable ? 'multiple' : 'none'}
        onRowAction={
          onRowPressed &&
          ((id) => {
            const rowDisabled =
              computedDisabledKeys?.has(id as string | number) ?? false;
            if (!rowDisabled) {
              onRowPressed(id as string);
            }
          })
        }
        onSelectionChange={onSelectionChange}
        sortDescriptor={sortedBy}
        onSortChange={handleSortChange}
        classNames={{
          wrapper: cn('px-0 py-0', {
            'dark:bg-transparent': tableVariant === 'transparent',
          }),
          th: cn({
            'dark:bg-default-200 dark:before:bg-default-200 dark:text-foreground py-2':
              tableVariant === 'transparent',
          }),
          tr: cn({
            'cursor-pointer': !!onRowPressed || isSelectable,
            '[&:not([data-disabled=true]):hover>td]:before:opacity-70':
              !isLoading,
            '[&:last-child>td]:border-b-0': true,
            '[&:first-child>td:first-child]:before:rounded-ss-xl [&:first-child>td:last-child]:before:rounded-se-xl': true,
            '[&:last-child>td:first-child]:before:rounded-es-xl [&:last-child>td:last-child]:before:rounded-ee-xl': true,
            '[&[data-disabled=true]]:cursor-not-allowed [&[data-disabled=true]>td:not(:last-child)]:opacity-50': true,
          }),
          td: cn(
            {
              'border-b border-default-100': tableVariant !== 'transparent',
              'dark:border-b dark:border-default-200/50':
                tableVariant === 'transparent',
              'before:-z-[1]': true,
              'before:bg-default-100': true,
              '[&:first-child]:before:rounded-s-none [&:last-child]:before:rounded-e-none': true,
            },
            tableVariant === 'transparent' &&
              'dark:bg-transparent dark:before:bg-default-200 dark:before:opacity-0 py-3',
          ),
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
              className={`align-middle ${column.hasDescription ? 'h-14' : ''} ${column.className || ''}`}
              key={column.key as string}
              width={column.width}
              maxWidth={column.maxWidth}
              minWidth={column.minWidth}
              allowsSorting={column.sortable}
            >
              {column.key ? (
                <div className="inline-flex flex-col">
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
