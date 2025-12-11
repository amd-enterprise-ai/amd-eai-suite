// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';

import { TimeSeriesData, TimeRange } from '@/types/metrics';
import { mockWorkloads } from '@/__mocks__/services/app/workloads.data';
import EndToEndLatencyCard from '@/components/features/workloads/EndToEndLatencyCard';

import wrapper from '@/__tests__/ProviderWrapper';

// Mock formatSeconds utility
vi.mock('@/utils/app/strings', () => ({
  formatSeconds: vi.fn((value) => `${value}s`),
}));

// Mock next-i18next
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('EndToEndLatencyCard', () => {
  const mockTimeSeriesData: TimeSeriesData = {
    metadata: {
      __name__: 'test_metric',
      instance: 'test-instance',
    },
    values: [
      { timestamp: '2023-01-01T00:00:00Z', value: 0.5 },
      { timestamp: '2023-01-01T01:00:00Z', value: 0.7 },
      { timestamp: '2023-01-01T02:00:00Z', value: 0.3 },
    ],
  };

  const mockTimeRange: TimeRange = {
    start: new Date('2023-01-01T00:00:00Z'),
    end: new Date('2023-01-01T02:00:00Z'),
  };

  const defaultProps = {
    workload: mockWorkloads[0],
    timeRange: mockTimeRange,
    width: 460,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the card with default props', () => {
    render(<EndToEndLatencyCard {...defaultProps} />, { wrapper });

    expect(
      screen.getByText('details.metrics.endToEndLatency.title'),
    ).toBeInTheDocument();
  });
});
