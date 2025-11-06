// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ActionItem, TableColumn } from '@/types/data-table/clientside-table';

import ThreeDotActionsDropdown from '@/components/shared/Dropdown/ThreeDotActionsDropdown';

export const ACTIONS_COLUMN_KEY = 'actions';

export const ACTIONS_COLUMN = {
  key: ACTIONS_COLUMN_KEY,
  width: 1,
  sortable: false,
} as TableColumn<typeof ACTIONS_COLUMN_KEY>;

/**
 * Creates a renderer for an actions column in a data table that resolves actions from function or direct array
 * @param rowActions The actions to display for each row, or a function to generate them
 * @param item The data item for the current row
 */
export const getActionsColumnRenderer = <T,>(
  rowActions: ActionItem<T>[] | ((item: T) => ActionItem<T>[]),
  item: T,
) => {
  const actions =
    typeof rowActions === 'function' ? rowActions(item) : rowActions;

  return <ThreeDotActionsDropdown actions={actions} item={item} />;
};
