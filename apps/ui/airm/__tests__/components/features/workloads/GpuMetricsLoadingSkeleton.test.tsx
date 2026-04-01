// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';

import { GpuMetricsLoadingSkeleton } from '@/components/features/workloads/GpuMetricsLoadingSkeleton';

import wrapper from '@/__tests__/ProviderWrapper';

vi.mock('@amdenterpriseai/components', () => ({
  StatsWithLineChart: ({
    title,
    isLoading,
  }: {
    title: string;
    isLoading: boolean;
  }) => (
    <div data-testid="stats-chart" data-loading={isLoading}>
      {title}
    </div>
  ),
}));

describe('GpuMetricsLoadingSkeleton', () => {
  it('should render 6 chart placeholders (2 rows x 3 metrics)', () => {
    render(<GpuMetricsLoadingSkeleton />, { wrapper });
    const charts = screen.getAllByTestId('stats-chart');
    expect(charts).toHaveLength(6);
  });

  it('should render metric titles for each row', () => {
    render(<GpuMetricsLoadingSkeleton />, { wrapper });
    const memoryTitles = screen.getAllByText(
      'details.fields.memoryUtilization',
    );
    const tempTitles = screen.getAllByText(
      'details.fields.junctionTemperature',
    );
    const powerTitles = screen.getAllByText('details.fields.gpuPowerUsage');
    expect(memoryTitles).toHaveLength(2);
    expect(tempTitles).toHaveLength(2);
    expect(powerTitles).toHaveLength(2);
  });

  it('should pass isLoading to all charts', () => {
    render(<GpuMetricsLoadingSkeleton />, { wrapper });
    const charts = screen.getAllByTestId('stats-chart');
    for (const chart of charts) {
      expect(chart).toHaveAttribute('data-loading', 'true');
    }
  });
});
