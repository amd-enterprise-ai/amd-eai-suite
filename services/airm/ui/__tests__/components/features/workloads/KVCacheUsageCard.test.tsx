// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';

import { MetricScalarResponse, TimeRange } from '@/types/metrics';
import { mockWorkloads } from '@/__mocks__/services/app/workloads.data';
import KVCacheUsageCard from '@/components/features/workloads/KVCacheUsageCard';

import wrapper from '@/__tests__/ProviderWrapper';

// Mock displayPercentage utility
vi.mock('@/utils/app/strings', () => ({
  displayPercentage: vi.fn((value) => `${value}%`),
}));

// Mock next-i18next
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('KVCacheUsageCard', () => {
  const mockMetricScalarResponse: MetricScalarResponse = {
    data: 75.5,
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
    render(<KVCacheUsageCard {...defaultProps} />, { wrapper });

    expect(
      screen.getByText('details.metrics.kvCacheUsage.title'),
    ).toBeInTheDocument();
  });
});
