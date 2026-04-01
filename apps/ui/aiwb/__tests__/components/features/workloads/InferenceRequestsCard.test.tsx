// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';

import { TimeRangePeriod } from '@amdenterpriseai/types';
import { mockWorkloads } from '@/__mocks__/services/app/workloads.data';
import InferenceRequestsCard from '@/components/features/workloads/InferenceRequestsCard';

import wrapper from '@/__tests__/ProviderWrapper';

// Mock chart utils from workloads
vi.mock('@/lib/app/workloads', async (importOriginal) => ({
  ...(await importOriginal()),
  getTickGap: vi.fn((timePeriod: string) => (timePeriod === '1h' ? 1 : 2)),
  transformTimeSeriesDataToChartData: vi.fn(
    (_tsd: unknown, _timestamps: string[], _metadataKey: string) => ({
      data: [],
      categories: [],
    }),
  ),
}));

// Mock next-i18next
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('InferenceRequestsCard', () => {
  const mockData = {
    data: [
      {
        date: '2023-01-01T00:00:00Z',
        running_requests: 5,
        waiting_requests: 3,
      },
      {
        date: '2023-01-01T01:00:00Z',
        running_requests: 7,
        waiting_requests: 2,
      },
      {
        date: '2023-01-01T02:00:00Z',
        running_requests: 4,
        waiting_requests: 1,
      },
    ],
    categories: ['running_requests', 'waiting_requests'],
  };

  const defaultProps = {
    namespace: 'test-project-id',
    workloadId: mockWorkloads[0].id,
    timePeriod: TimeRangePeriod['1H'],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the card with default props', () => {
    render(<InferenceRequestsCard {...defaultProps} />, { wrapper });

    expect(
      screen.getByText('details.metrics.inferenceRequests.title'),
    ).toBeInTheDocument();
  });
});
