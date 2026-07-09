// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { DropdownActionItem } from './types';

export type FlattenedDropdownItem = DropdownActionItem & {
  isSectionHeader?: boolean;
};

export const isActionDisabled = (action: DropdownActionItem): boolean => {
  return !!action.isDisabled;
};

export const isSectionHeader = (action: FlattenedDropdownItem): boolean => {
  return !!action.isSectionHeader;
};

export const hasNestedActions = (action: FlattenedDropdownItem): boolean => {
  return (
    !!action.actions && action.actions.length > 0 && !isSectionHeader(action)
  );
};

export const canExecuteAction = (action: FlattenedDropdownItem): boolean => {
  return !isSectionHeader(action) && !isActionDisabled(action);
};
