// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, render, screen } from '@testing-library/react';

import {
  Table,
  TableBody,
  TableCell,
  TableColumn,
  TableHeader,
  TableRow,
  getKeyValue,
  type SortDescriptor,
} from '@/src/DataTable/TablePrimitive';

type Row = { id: string; name: string; score: number };

const columns = [
  { key: 'name', label: 'Name' },
  { key: 'score', label: 'Score' },
];

const rows: Row[] = [
  { id: '1', name: 'Alpha', score: 10 },
  { id: '2', name: 'Beta', score: 20 },
];

describe('TablePrimitive', () => {
  it('re-exports HeroUI Table with compound sub-components', () => {
    expect(Table.Header).toBe(TableHeader);
    expect(Table.Column).toBe(TableColumn);
    expect(Table.Body).toBe(TableBody);
    expect(Table.Row).toBe(TableRow);
    expect(Table.Cell).toBe(TableCell);
  });

  it('renders rows using flat alias imports', async () => {
    await act(() => {
      render(
        <Table aria-label="Test table">
          <TableHeader columns={columns}>
            {(column) => (
              <TableColumn key={column.key}>{column.label}</TableColumn>
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
        </Table>,
      );
    });

    expect(screen.getByText('Alpha')).toBeInTheDocument();
    expect(screen.getByText('Beta')).toBeInTheDocument();
    expect(screen.getByText('20')).toBeInTheDocument();
  });

  it('passes sortDescriptor through to sortable columns', async () => {
    const sortDescriptor: SortDescriptor = {
      column: 'score',
      direction: 'descending',
    };

    await act(() => {
      render(
        <Table aria-label="Sortable table" sortDescriptor={sortDescriptor}>
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
        </Table>,
      );
    });

    const scoreHeader = screen.getByRole('columnheader', { name: 'Score' });
    expect(scoreHeader).toHaveAttribute('aria-sort', 'descending');
  });

  it('renders using compound API aliases on Table', async () => {
    await act(() => {
      render(
        <Table aria-label="Compound API table">
          <Table.Header columns={columns}>
            {(column) => (
              <Table.Column key={column.key}>{column.label}</Table.Column>
            )}
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
        </Table>,
      );
    });

    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Alpha')).toBeInTheDocument();
  });
});
