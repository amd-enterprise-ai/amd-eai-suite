// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';

import { TimeSeriesData, TimeRange } from '@/types/metrics';
import { Workload } from '@/types/workloads';
import { WorkloadType, WorkloadStatus } from '@/types/enums/workloads';
import InterTokenLatencyCard from '@/components/features/workloads/InterTokenLatencyCard';

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

describe('InterTokenLatencyCard', () => {
  const mockTimeSeriesData: TimeSeriesData = {
    metadata: {
      __name__: 'test_metric',
      instance: 'test-instance',
    },
    values: [
      { timestamp: '2023-01-01T00:00:00Z', value: 0.1 },
      { timestamp: '2023-01-01T01:00:00Z', value: 0.15 },
      { timestamp: '2023-01-01T02:00:00Z', value: 0.08 },
    ],
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

  const defaultProps = {
    workload: mockWorkload,
    timeRange: mockTimeRange,
    width: 460,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the card with default props', () => {
    render(<InterTokenLatencyCard {...defaultProps} />, { wrapper });

    expect(
      screen.getByText('details.metrics.interTokenLatency.title'),
    ).toBeInTheDocument();
  });
});
