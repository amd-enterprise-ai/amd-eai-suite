// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { Story, StoryDefault } from '@ladle/react';
import { useState } from 'react';

import {
  Table,
  TableBody,
  TableCell,
  TableColumn,
  TableHeader,
  TableRow,
  getKeyValue,
  type SortDescriptor,
} from '../src/DataTable/TablePrimitive';

export default {
  title: 'Components/Table',
} satisfies StoryDefault;

type Row = { id: string; name: string; role: string };

const columns = [
  { key: 'name', label: 'Name' },
  { key: 'role', label: 'Role' },
];

const rows: Row[] = [
  { id: '1', name: 'Ada Lovelace', role: 'Engineer' },
  { id: '2', name: 'Grace Hopper', role: 'Admiral' },
  { id: '3', name: 'Katherine Johnson', role: 'Mathematician' },
];

export const FlatAliases: Story = () => {
  const [sortDescriptor, setSortDescriptor] = useState<SortDescriptor>({
    column: 'name',
    direction: 'ascending',
  });

  return (
    <Table
      aria-label="Team members"
      sortDescriptor={sortDescriptor}
      onSortChange={setSortDescriptor}
    >
      <TableHeader columns={columns}>
        {(column) => (
          <TableColumn key={column.key} allowsSorting>
            {column.label}
          </TableColumn>
        )}
      </TableHeader>
      <TableBody items={rows}>
        {(item) => (
          <TableRow key={item.id}>
            {(columnKey) => (
              <TableCell>{getKeyValue(item, columnKey)}</TableCell>
            )}
          </TableRow>
        )}
      </TableBody>
    </Table>
  );
};

export const CompoundAPI: Story = () => (
  <Table aria-label="Team members (compound API)">
    <Table.Header columns={columns}>
      {(column) => <Table.Column key={column.key}>{column.label}</Table.Column>}
    </Table.Header>
    <Table.Body items={rows}>
      {(item) => (
        <Table.Row key={item.id}>
          {(columnKey) => (
            <Table.Cell>{getKeyValue(item, columnKey)}</Table.Cell>
          )}
        </Table.Row>
      )}
    </Table.Body>
  </Table>
);
