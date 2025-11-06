// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, render, screen } from '@testing-library/react';

import { CategorySplitStatsCard } from '@/components/shared/Metrics/CategorySplitStatsCard';

describe('CategorySplitStatsCard', () => {
  it('renders component', () => {
    const { container } = render(
      <CategorySplitStatsCard
        title={'Test Card title'}
        total={90}
        data={null}
      />,
    );
    expect(container).toBeTruthy();
    expect(screen.getByText('Test Card title')).toBeInTheDocument();
  });

  it('renders component with total shown', () => {
    act(() => {
      render(
        <CategorySplitStatsCard
          title={'Test Card title'}
          total={90}
          data={null}
        />,
      );
    });
    expect(screen.getByText('90')).toBeInTheDocument();
  });

  it('renders component with total shown', () => {
    const mockData = [
      { label: 'Category 1', value: 30 },
      { label: 'Category 2', value: 40 },
      { label: 'Category 3', value: 20 },
    ];

    act(() => {
      render(
        <CategorySplitStatsCard
          title={'Test Card title'}
          total={90}
          data={{
            total: 100,
            title: 'test subtitle',
            values: mockData,
          }}
        />,
      );
    });
    expect(screen.getByText('test subtitle')).toBeInTheDocument();
    expect(screen.getByText('Category 1')).toBeInTheDocument();
    expect(screen.getByText('Category 2')).toBeInTheDocument();
    expect(screen.getByText('Category 3')).toBeInTheDocument();
    const ratioElements = screen.getAllByText('(', { exact: false });
    expect(ratioElements[0].parentElement).toHaveTextContent('(30/100)');
    expect(ratioElements[1].parentElement).toHaveTextContent('(40/100)');
    expect(ratioElements[2].parentElement).toHaveTextContent('(20/100)');
  });

  it('renders component in loading state', () => {
    const mockData = [
      { label: 'Category 1', value: 30 },
      { label: 'Category 2', value: 40 },
      { label: 'Category 3', value: 20 },
    ];

    act(() => {
      render(
        <CategorySplitStatsCard
          title={'Test Card title'}
          total={90}
          data={null}
          isLoading
        />,
      );
    });
    expect(screen.queryByText('90')).not.toBeInTheDocument();
  });
});
