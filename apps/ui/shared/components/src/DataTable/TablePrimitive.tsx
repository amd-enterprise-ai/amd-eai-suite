// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Table as HeroUITable,
  TableBody as HeroUITableBody,
  TableCell as HeroUITableCell,
  TableColumn as HeroUITableColumn,
  TableHeader as HeroUITableHeader,
  TableRow as HeroUITableRow,
  getKeyValue as heroUIGetKeyValue,
  type SortDescriptor,
} from '@heroui/react';

const Table = Object.assign(HeroUITable, {
  Header: HeroUITableHeader,
  Column: HeroUITableColumn,
  Body: HeroUITableBody,
  Row: HeroUITableRow,
  Cell: HeroUITableCell,
});

export {
  Table,
  HeroUITableBody as TableBody,
  HeroUITableCell as TableCell,
  HeroUITableColumn as TableColumn,
  HeroUITableHeader as TableHeader,
  HeroUITableRow as TableRow,
  heroUIGetKeyValue as getKeyValue,
  type SortDescriptor,
};
