// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { DynamicValueLegend } from '@amdenterpriseai/components';
import type { AvailableChartColorsKeys } from '@amdenterpriseai/types';

const categories = ['gpu-1', 'gpu-2', 'gpu-3'];
const colors: AvailableChartColorsKeys[] = ['blue', 'emerald', 'amber'];
const data = [{ date: '2026-01-01', 'gpu-1': 42, 'gpu-2': 75, 'gpu-3': 90 }];

const defaultProps = {
  categories,
  colors,
  data,
  unit: '%',
};

describe('DynamicValueLegend', () => {
  it('renders category labels and formatted values', () => {
    render(<DynamicValueLegend {...defaultProps} />);

    expect(screen.getByText('gpu-1')).toBeInTheDocument();
    expect(screen.getByText('gpu-2')).toBeInTheDocument();
    expect(screen.getByText('gpu-3')).toBeInTheDocument();
    expect(screen.getByText('42%')).toBeInTheDocument();
    expect(screen.getByText('75%')).toBeInTheDocument();
    expect(screen.getByText('90%')).toBeInTheDocument();
  });

  it('uses valueFormatter when provided', () => {
    render(
      <DynamicValueLegend
        {...defaultProps}
        valueFormatter={(v) => `${v} watts`}
      />,
    );

    expect(screen.getByText('42 watts')).toBeInTheDocument();
    expect(screen.getByText('75 watts')).toBeInTheDocument();
  });

  it('shows N/A when data point has no value for a category', () => {
    render(
      <DynamicValueLegend
        {...defaultProps}
        data={[{ date: '2026-01-01', 'gpu-1': 42 }]}
      />,
    );

    expect(screen.getByText('42%')).toBeInTheDocument();
    expect(screen.getAllByText('N/A')).toHaveLength(2);
  });

  it('renders skeleton placeholders when isLoading is true', () => {
    const { container } = render(
      <DynamicValueLegend {...defaultProps} isLoading />,
    );

    expect(screen.queryByText('gpu-1')).not.toBeInTheDocument();
    expect(screen.queryByText('gpu-2')).not.toBeInTheDocument();

    const skeletonItems = container.querySelectorAll('.animate-pulse');
    expect(skeletonItems.length).toBeGreaterThan(0);
  });

  it('renders 8 skeleton items by default when loading', () => {
    const { container } = render(
      <DynamicValueLegend {...defaultProps} isLoading />,
    );

    const grid = container.firstElementChild!;
    expect(grid.children).toHaveLength(8);
  });

  it('respects custom loadingItemCount', () => {
    const { container } = render(
      <DynamicValueLegend {...defaultProps} isLoading loadingItemCount={3} />,
    );

    const grid = container.firstElementChild!;
    expect(grid.children).toHaveLength(3);
  });

  it('does not render category buttons when loading', () => {
    render(<DynamicValueLegend {...defaultProps} isLoading />);

    expect(screen.queryAllByRole('button')).toHaveLength(0);
  });

  it('renders category buttons when not loading', () => {
    render(<DynamicValueLegend {...defaultProps} />);

    expect(screen.getAllByRole('button')).toHaveLength(3);
  });

  it('calls onCategoryClick when a legend item is clicked', async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();

    render(
      <DynamicValueLegend {...defaultProps} onCategoryClick={handleClick} />,
    );

    await user.click(screen.getByText('gpu-2'));
    expect(handleClick).toHaveBeenCalledWith('gpu-2');
  });

  it('applies active styling to the selected category', () => {
    render(<DynamicValueLegend {...defaultProps} activeCategory="gpu-1" />);

    const activeButton = screen.getByText('gpu-1').closest('button')!;
    expect(activeButton.className).toContain('border-gray-400');

    const dimmedButton = screen.getByText('gpu-2').closest('button')!;
    expect(dimmedButton.className).toContain('opacity-40');
  });

  it('uses displayPoint values when provided', () => {
    const displayPoint = { 'gpu-1': 10, 'gpu-2': 20, 'gpu-3': 30 };

    render(
      <DynamicValueLegend {...defaultProps} displayPoint={displayPoint} />,
    );

    expect(screen.getByText('10%')).toBeInTheDocument();
    expect(screen.getByText('20%')).toBeInTheDocument();
    expect(screen.getByText('30%')).toBeInTheDocument();
    expect(screen.queryByText('42%')).not.toBeInTheDocument();
  });
});
