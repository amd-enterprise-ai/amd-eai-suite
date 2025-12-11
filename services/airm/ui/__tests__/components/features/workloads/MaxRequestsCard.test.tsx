// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';

import { TimeRange } from '@/types/metrics';
import { mockWorkloads } from '@/__mocks__/services/app/workloads.data';
import MaxRequestsCard from '@/components/features/workloads/MaxRequestsCard';

import wrapper from '@/__tests__/ProviderWrapper';

// Mock next-i18next
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('MaxRequestsCard', () => {
  const mockData = {
    data: [
      { running_requests: 5, waiting_requests: 3 },
      { running_requests: 7, waiting_requests: 2 },
      { running_requests: 4, waiting_requests: 1 },
      { running_requests: 10, waiting_requests: 5 }, // This should be the max (15)
      { running_requests: 6, waiting_requests: 2 },
    ],
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
    render(<MaxRequestsCard {...defaultProps} />, { wrapper });

    expect(
      screen.getByText('details.metrics.maxRequests.title'),
    ).toBeInTheDocument();
  });
});
