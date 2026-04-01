// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { SortDirection } from '../enums/sort-direction';
import { UserTableField } from '../enums/user-table-fields';
import { User } from '../users';

export type UserField = keyof User;

export type UserColumns = Array<{
  key: UserTableField;
  sortable?: boolean;
  sortDirection?: SortDirection;
}>;
