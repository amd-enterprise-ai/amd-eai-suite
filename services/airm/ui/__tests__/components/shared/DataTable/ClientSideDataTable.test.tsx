// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, fireEvent, render, screen, within } from '@testing-library/react';

import { TFunction } from 'next-i18next';

import { PageFrameSize } from '@/types/enums/page-frame-size';

import ClientSideDataTable from '@/components/shared/DataTable/ClientSideDataTable';

const generateRandomData = (numEntries: number) => {
  const names = [
    'Alice',
    'Bob',
    'Charlie',
    'David',
    'Eve',
    'Frank',
    'Grace',
    'Hank',
    'Ivy',
    'Jack',
  ];
  const data = [];
  for (let i = 0; i < numEntries; i++) {
    const id = i + 1;
    const name = names[Math.floor(Math.random() * names.length)];
    const age = Math.floor(Math.random() * 60) + 20; // Random age between 20 and 80
    data.push({ id, name, age });
  }
  return data;
};

describe('ClientSideDataTable', () => {
  const mockData = [
    { id: 1, name: 'Alice', age: 30 },
    { id: 2, name: 'Bob', age: 45 },
    { id: 3, name: 'Charlie', age: 35 },
  ];

  const mockColumns = [{ key: 'name' }, { key: 'age', sortable: true }];

  const mockTranslation = ((a: any) => a) as TFunction;

  it('should set render sort button if sortable is set true on field', () => {
    act(() => {
      render(
        <ClientSideDataTable
          data={mockData}
          columns={mockColumns}
          defaultSortByField="name"
          translation={mockTranslation}
          idKey="id"
        />,
      );
    });

    const ageColumnHeader = screen.getByText('list.headers.age.title');

    expect(ageColumnHeader).toBeTruthy();
    expect(ageColumnHeader.parentElement?.parentElement).toHaveAttribute(
      'aria-sort',
      'none',
    );
  });

  it('should not render sort button if sortable is set to false on field', () => {
    act(() => {
      render(
        <ClientSideDataTable
          data={mockData}
          columns={mockColumns}
          defaultSortByField="name"
          translation={mockTranslation}
          idKey="id"
        />,
      );
    });

    const nameColumnHeader = screen.getByText('list.headers.name.title');
    expect(nameColumnHeader).toBeInTheDocument();
    expect(nameColumnHeader.parentElement?.parentElement).not.toHaveAttribute(
      'aria-sort',
    );
  });

  it('should display empty state message when data is empty', () => {
    act(() => {
      render(
        <ClientSideDataTable
          data={[]}
          columns={mockColumns}
          defaultSortByField="name"
          translation={mockTranslation}
          idKey="id"
        />,
      );
    });

    const emptyStateMessage = screen.getByText('list.empty.description');
    expect(emptyStateMessage).toBeInTheDocument();
  });

  it('should render cell data correctly', () => {
    act(() => {
      render(
        <ClientSideDataTable
          data={mockData}
          columns={mockColumns}
          defaultSortByField="name"
          translation={mockTranslation}
          idKey="id"
        />,
      );
    });

    // Check that the cell data is rendered correctly
    const aliceNameCell = screen.getByText('Alice');
    const bobNameCell = screen.getByText('Bob');
    const charlieNameCell = screen.getByText('Charlie');
    const aliceAgeCell = screen.getByText('30');
    const bobAgeCell = screen.getByText('45');
    const charlieAgeCell = screen.getByText('35');

    expect(aliceNameCell).toBeInTheDocument();
    expect(bobNameCell).toBeInTheDocument();
    expect(charlieNameCell).toBeInTheDocument();
    expect(aliceAgeCell).toBeInTheDocument();
    expect(bobAgeCell).toBeInTheDocument();
    expect(charlieAgeCell).toBeInTheDocument();
  });

  it('should not render the pagination component if the number of rows is less than the minimum page size ', () => {
    const mockData = generateRandomData(PageFrameSize.SMALL - 1);

    act(() => {
      render(
        <ClientSideDataTable
          data={mockData}
          columns={mockColumns}
          defaultSortByField="name"
          translation={mockTranslation}
          idKey="id"
        />,
      );
    });

    const pagination = screen.queryByLabelText(
      'list.pagination.pageSize.label',
    );
    expect(pagination).toBeFalsy();
  });

  it('should render the correct number of rows per when frame size changed', () => {
    const mockData = generateRandomData(30);

    act(() => {
      render(
        <ClientSideDataTable
          data={mockData}
          columns={mockColumns}
          defaultSortByField="name"
          translation={mockTranslation}
          idKey="id"
        />,
      );
    });

    act(() => {
      const pageFrameSelectWrapper = screen.queryByText(
        'list.pagination.pageSize.label',
      )?.nextElementSibling;
      const selectTrigger = (pageFrameSelectWrapper as Element).querySelector(
        'button[data-slot="trigger"]',
      );

      fireEvent.click(selectTrigger!);
    });

    act(() => {
      const select = screen.queryAllByRole('option');
      const mediumPageSize = select.find(
        (option) => option.textContent === PageFrameSize.MEDIUM.toString(),
      );
      fireEvent.click(mediumPageSize!);
    });

    const rows25 = screen.getAllByRole('row');
    expect(rows25).toHaveLength(PageFrameSize.MEDIUM + 1); // +1 for the header row
  });

  it('should render the correct number of rows per when frame size changed that fits all the rows', () => {
    const mockData = generateRandomData(30);

    act(() => {
      render(
        <ClientSideDataTable
          data={mockData}
          columns={mockColumns}
          defaultSortByField="name"
          translation={mockTranslation}
          idKey="id"
        />,
      );
    });

    act(() => {
      const pageFrameSelectWrapper = screen.queryByText(
        'list.pagination.pageSize.label',
      )?.nextElementSibling;
      const selectTrigger = (pageFrameSelectWrapper as Element).querySelector(
        'button[data-slot="trigger"]',
      );

      fireEvent.click(selectTrigger!);
    });

    act(() => {
      const select = screen.queryAllByRole('option');
      const largePageSize = select.find(
        (option) => option.textContent === PageFrameSize.LARGE.toString(),
      );
      fireEvent.click(largePageSize!);
    });

    const rows100 = screen.getAllByRole('row');
    expect(rows100).toHaveLength(31); // +1 for the header row
  });

  it('should render the correct number of rows in pagination', () => {
    const mockData = generateRandomData(35);

    act(() => {
      render(
        <ClientSideDataTable
          data={mockData}
          columns={mockColumns}
          defaultSortByField="name"
          translation={mockTranslation}
          idKey="id"
        />,
      );
    });

    const paginationButton = screen.getAllByLabelText('pagination item 2');
    fireEvent.click(paginationButton[0]);

    const rows = screen.getAllByRole('row');
    expect(rows).toHaveLength(PageFrameSize.SMALL + 1); // +1 for the header row
  });

  it('should render the correct number of rows in pagination on the last frame', () => {
    const mockData = generateRandomData(35);

    act(() => {
      render(
        <ClientSideDataTable
          data={mockData}
          columns={mockColumns}
          defaultSortByField="name"
          translation={mockTranslation}
          idKey="id"
        />,
      );
    });

    const paginationButton = screen.getAllByLabelText('pagination item 4');
    fireEvent.click(paginationButton[0]);

    const rows = screen.getAllByRole('row');
    expect(rows).toHaveLength(6); // +1 for the header row
  });

  it('should render the correct number of rows in pagination with selected frame size', async () => {
    const mockData = generateRandomData(76);

    await act(() => {
      render(
        <ClientSideDataTable
          data={mockData}
          columns={mockColumns}
          defaultSortByField="name"
          translation={mockTranslation}
          idKey="id"
        />,
      );
    });

    act(() => {
      const paginationButton = screen.getAllByLabelText('pagination item 2');
      fireEvent.click(paginationButton[0]);

      const pageFrameSelectWrapper = screen.queryByText(
        'list.pagination.pageSize.label',
      )?.nextElementSibling;
      const selectTrigger = (pageFrameSelectWrapper as Element).querySelector(
        'button[data-slot="trigger"]',
      );

      fireEvent.click(selectTrigger!);
    });

    act(() => {
      const select = screen.queryAllByRole('option');
      const mediumPageSize = select.find(
        (option) => option.textContent === PageFrameSize.MEDIUM.toString(),
      );
      fireEvent.click(mediumPageSize!);
    });

    const rows = await screen.getAllByRole('row');
    expect(rows).toHaveLength(PageFrameSize.MEDIUM + 1); // +1 for the header row
  });

  it('should call onRowPressed when a row is clicked', () => {
    const mockOnRowPressed = vi.fn();

    act(() => {
      render(
        <ClientSideDataTable
          data={mockData}
          columns={mockColumns}
          defaultSortByField="name"
          translation={mockTranslation}
          idKey="id"
          onRowPressed={mockOnRowPressed}
        />,
      );
    });

    act(() => {
      const aliceRow = screen.getByText('Alice').closest('tr');
      if (aliceRow) {
        fireEvent.click(aliceRow);
      }
    });

    expect(mockOnRowPressed).toHaveBeenCalledWith('1');
  });

  it('should call the corresponding action handler when an action is clicked', () => {
    const mockDeleteAction = vi.fn();

    act(() => {
      render(
        <ClientSideDataTable
          data={mockData}
          columns={mockColumns}
          defaultSortByField="name"
          translation={mockTranslation}
          idKey="id"
          rowActions={[
            {
              key: 'delete',
              onPress: mockDeleteAction,
              label: 'Delete',
            },
            {
              key: 'copy',
              onPress: () => {},
              label: 'copy',
            },
          ]}
        />,
      );
    });

    act(() => {
      const aliceRow = screen.getByText('Bob').closest('tr');
      expect(aliceRow).toBeTruthy();
      const dropDown = within(aliceRow!).getByLabelText('list.actions.label');
      fireEvent.click(dropDown);
    });

    act(() => {
      fireEvent.click(screen.getByText('Delete'));
    });

    expect(mockDeleteAction).toHaveBeenCalledWith({
      id: 2,
      name: 'Bob',
      age: 45,
    });
  });

  it('should render the description if a column needs it', () => {
    const columns = [
      { key: 'name' },
      { key: 'age', sortable: true, hasDescription: true },
    ];
    act(() => {
      render(
        <ClientSideDataTable
          data={[]}
          columns={columns}
          defaultSortByField="name"
          translation={mockTranslation}
          idKey="id"
        />,
      );
    });

    const emptyStateMessage = screen.getByText('list.headers.age.description');
    expect(emptyStateMessage).toBeInTheDocument();
  });
});
