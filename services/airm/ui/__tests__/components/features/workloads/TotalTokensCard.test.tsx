// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';

import { MetricScalarResponse, TimeRange } from '@/types/metrics';
import { mockWorkloads } from '@/__mocks__/services/app/workloads.data';
import TotalTokensCard from '@/components/features/workloads/TotalTokensCard';

import wrapper from '@/__tests__/ProviderWrapper';

// Mock the shared Metrics components
vi.mock('@/components/shared/Metrics/StatisticsCard', () => ({
  StatisticsCard: vi.fn(
    ({ title, tooltip, statistic, statisticFormatter, isLoading }) => (
      <div data-testid="statistics-card">
        <div data-testid="title">{title}</div>
        <div data-testid="tooltip">{tooltip}</div>
        <div data-testid="statistic">{statistic}</div>
        <div data-testid="loading">{isLoading ? 'true' : 'false'}</div>
        <div data-testid="formatter">
          {statisticFormatter ? 'formatTokens' : 'none'}
        </div>
      </div>
    ),
  ),
}));

// Mock formatTokens utility
vi.mock('@/utils/app/strings', () => ({
  formatTokens: vi.fn((value) => `${value} tokens`),
}));

// Mock next-i18next
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('TotalTokensCard', () => {
  const mockMetricScalarResponse: MetricScalarResponse = {
    data: 125000,
    range: {
      start: '2023-01-01T00:00:00Z',
      end: '2023-01-01T02:00:00Z',
    },
  };

  const mockTimeRange: TimeRange = {
    start: new Date('2023-01-01T00:00:00Z'),
    end: new Date('2023-01-01T02:00:00Z'),
  };

  const defaultProps = {
    workload: mockWorkloads[0],
    timeRange: mockTimeRange,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the card with default props', () => {
    render(<TotalTokensCard {...defaultProps} />, { wrapper });

    expect(
      screen.getByText('details.metrics.totalTokens.title'),
    ).toBeInTheDocument();
  });
});
