// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { SortDirection } from '@/types/enums/sort-direction';
import { UserTableField } from '@/types/enums/user-table-fields';
import { User } from '@/types/users';

export type UserField = keyof User;

export type UserColumns = Array<{
  key: UserTableField;
  sortable?: boolean;
  sortDirection?: SortDirection;
}>;
