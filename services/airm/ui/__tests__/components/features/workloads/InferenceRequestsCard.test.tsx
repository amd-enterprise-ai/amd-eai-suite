// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import { RefObject } from 'react';

import { TimeRangePeriod } from '@/types/enums/metrics';
import { TimeRange } from '@/types/metrics';
import { Workload } from '@/types/workloads';
import { WorkloadType, WorkloadStatus } from '@/types/enums/workloads';
import InferenceRequestsCard from '@/components/features/workloads/InferenceRequestsCard';

import wrapper from '@/__tests__/ProviderWrapper';

// Mock chart utils
vi.mock('@/utils/app/charts', () => ({
  getTickGap: vi.fn((timePeriod) => (timePeriod === '1h' ? 1 : 2)),
  generateSkeletonChartData: vi.fn(() => {}),
  isOver1Day: vi.fn(() => {}),
  getFirstTimestampsOfDayIndices: vi.fn(() => {}),
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

  const mockWorkload: Workload = {
    id: 'test-workload-id',
    type: WorkloadType.INFERENCE,
    name: 'test-workload',
    displayName: 'Test Inference Workload',
    createdBy: 'test-user',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
    status: WorkloadStatus.RUNNING,
    chartId: 'test-chart-id',
    clusterId: 'test-cluster-id',
    cluster: {
      id: 'test-cluster-id',
      name: 'Test Cluster',
      lastHeartbeatAt: '2024-01-01T00:00:00Z',
      status: 'online' as any,
    },
  };

  const mockTimeRange: TimeRange = {
    start: new Date('2023-01-01T00:00:00Z'),
    end: new Date('2023-01-01T02:00:00Z'),
  };

  const mockTimeRangePeriod = TimeRangePeriod['1H'];

  const defaultProps = {
    workload: mockWorkload,
    timeRange: mockTimeRange,
    timeRangePeriod: mockTimeRangePeriod,
    width: 600,
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
