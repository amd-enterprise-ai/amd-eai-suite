// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { QueryClient } from '@tanstack/react-query';

import { InferenceMetrics } from '@/components/features/workloads/InferenceMetrics';
import { Workload } from '@/types/workloads';
import { WorkloadStatus, WorkloadType } from '@/types/enums/workloads';
import { TimeRangePeriod } from '@/types/enums/metrics';
import { TimeRange } from '@/types/metrics';
import { mockWorkloads } from '@/__mocks__/services/app/workloads.data';

import wrapper from '@/__tests__/ProviderWrapper';

// Mock the ProjectContext
vi.mock('@/contexts/ProjectContext', () => ({
  useProject: () => ({
    activeProject: 'test-project-id',
  }),
}));

// Mock next-i18next
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// Mock the time range utility
vi.mock('@/utils/app/time-range', () => ({
  getCurrentTimeRange: vi.fn((period) => ({
    start: new Date('2024-01-01T00:00:00Z'),
    end: new Date('2024-01-01T01:00:00Z'),
  })),
}));

// Mock the ChartTimeSelector component
vi.mock('@/components/shared/Metrics/ChartTimeSelector', () => ({
  ChartTimeSelector: vi.fn(
    ({
      onTimeRangeChange,
      onChartsRefresh,
      initialTimePeriod,
      translationPrefix,
      isFetching,
      lastFetchedTimestamp,
    }) => (
      <div data-testid="chart-time-selector">
        <button
          data-testid="time-range-button"
          onClick={() =>
            onTimeRangeChange(TimeRangePeriod['24H'], {
              start: new Date('2024-01-01T00:00:00Z'),
              end: new Date('2024-01-01T06:00:00Z'),
            })
          }
        >
          Change Time Range
        </button>
        <button data-testid="refresh-button" onClick={onChartsRefresh}>
          Refresh
        </button>
        <div data-testid="initial-period">{initialTimePeriod}</div>
        <div data-testid="translation-prefix">{translationPrefix}</div>
        <div data-testid="is-fetching">{isFetching ? 'true' : 'false'}</div>
        <div data-testid="last-fetched">
          {lastFetchedTimestamp?.toISOString()}
        </div>
      </div>
    ),
  ),
}));

// Mock all the metric card components
vi.mock('@/components/features/workloads/TimeToFirstTokenCard', () => ({
  default: vi.fn(({ workload, timeRange }) => (
    <div data-testid="time-to-first-token-card">
      <div data-testid="workload-id">{workload.id}</div>
      <div data-testid="time-range">{JSON.stringify(timeRange)}</div>
    </div>
  )),
}));

vi.mock('@/components/features/workloads/InterTokenLatencyCard', () => ({
  default: vi.fn(({ workload, timeRange }) => (
    <div data-testid="inter-token-latency-card">
      <div data-testid="workload-id">{workload.id}</div>
      <div data-testid="time-range">{JSON.stringify(timeRange)}</div>
    </div>
  )),
}));

vi.mock('@/components/features/workloads/EndToEndLatencyCard', () => ({
  default: vi.fn(({ workload, timeRange }) => (
    <div data-testid="end-to-end-latency-card">
      <div data-testid="workload-id">{workload.id}</div>
      <div data-testid="time-range">{JSON.stringify(timeRange)}</div>
    </div>
  )),
}));

vi.mock('@/components/features/workloads/InferenceRequestsCard', () => ({
  default: vi.fn(({ workload, timeRange, timeRangePeriod }) => (
    <div data-testid="inference-requests-card">
      <div data-testid="workload-id">{workload.id}</div>
      <div data-testid="time-range">{JSON.stringify(timeRange)}</div>
      <div data-testid="time-range-period">{timeRangePeriod}</div>
    </div>
  )),
}));

vi.mock('@/components/features/workloads/MaxRequestsCard', () => ({
  default: vi.fn(({ workload, timeRange }) => (
    <div data-testid="max-requests-card">
      <div data-testid="workload-id">{workload.id}</div>
      <div data-testid="time-range">{JSON.stringify(timeRange)}</div>
    </div>
  )),
}));

vi.mock('@/components/features/workloads/TotalTokensCard', () => ({
  default: vi.fn(({ workload, timeRange }) => (
    <div data-testid="total-tokens-card">
      <div data-testid="workload-id">{workload.id}</div>
      <div data-testid="time-range">{JSON.stringify(timeRange)}</div>
    </div>
  )),
}));

vi.mock('@/components/features/workloads/KVCacheUsageCard', () => ({
  default: vi.fn(({ workload, timeRange }) => (
    <div data-testid="kv-cache-usage-card">
      <div data-testid="workload-id">{workload.id}</div>
      <div data-testid="time-range">{JSON.stringify(timeRange)}</div>
    </div>
  )),
}));

// Mock useIsFetching hook and useQueryClient
const mockUseIsFetching = vi.fn();
const mockInvalidateQueries = vi.fn();
const mockUseQueryClient = vi.fn(() => ({
  invalidateQueries: mockInvalidateQueries,
}));

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual('@tanstack/react-query');
  return {
    ...actual,
    useIsFetching: () => mockUseIsFetching(),
    useQueryClient: () => mockUseQueryClient(),
  };
});

describe('InferenceMetrics', () => {
  const mockWorkload = mockWorkloads[0]; // Use first workload from shared mocks

  const defaultTimeRange: TimeRange = {
    start: new Date('2024-01-01T00:00:00Z'),
    end: new Date('2024-01-01T01:00:00Z'),
  };

  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    mockUseIsFetching.mockReturnValue(0);
    mockInvalidateQueries.mockClear();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders the inference metrics component with all metric cards', () => {
    render(<InferenceMetrics workload={mockWorkload} />, { wrapper });

    // Check ChartTimeSelector
    expect(screen.getByTestId('chart-time-selector')).toBeInTheDocument();
    expect(screen.getByTestId('initial-period')).toHaveTextContent('1h');
    expect(screen.getByTestId('translation-prefix')).toHaveTextContent(
      'timeRange',
    );

    // Check all metric cards are rendered
    expect(screen.getByTestId('time-to-first-token-card')).toBeInTheDocument();
    expect(screen.getByTestId('inter-token-latency-card')).toBeInTheDocument();
    expect(screen.getByTestId('end-to-end-latency-card')).toBeInTheDocument();
    expect(screen.getByTestId('inference-requests-card')).toBeInTheDocument();
    expect(screen.getByTestId('max-requests-card')).toBeInTheDocument();
    expect(screen.getByTestId('total-tokens-card')).toBeInTheDocument();
    expect(screen.getByTestId('kv-cache-usage-card')).toBeInTheDocument();
  });

  it('passes correct props to metric cards', () => {
    render(<InferenceMetrics workload={mockWorkload} />, { wrapper });

    // Check workload ID is passed to all cards
    const workloadIdElements = screen.getAllByTestId('workload-id');
    workloadIdElements.forEach((element) => {
      expect(element).toHaveTextContent('workload-1');
    });

    // Check time range is passed to all cards
    const timeRangeElements = screen.getAllByTestId('time-range');
    timeRangeElements.forEach((element) => {
      expect(element).toHaveTextContent(JSON.stringify(defaultTimeRange));
    });

    // Check that InferenceRequestsCard receives the time range period
    expect(screen.getByTestId('time-range-period')).toHaveTextContent('1h');
  });

  it('handles time range changes', () => {
    render(<InferenceMetrics workload={mockWorkload} />, { wrapper });

    const timeRangeButton = screen.getByTestId('time-range-button');
    fireEvent.click(timeRangeButton);

    // After clicking, the time range should be updated
    const timeRangeElements = screen.getAllByTestId('time-range');
    const newTimeRange = {
      start: new Date('2024-01-01T00:00:00Z'),
      end: new Date('2024-01-01T06:00:00Z'),
    };
    timeRangeElements.forEach((element) => {
      expect(element).toHaveTextContent(JSON.stringify(newTimeRange));
    });
  });

  it('shows fetching state correctly', () => {
    mockUseIsFetching.mockReturnValue(1);

    render(<InferenceMetrics workload={mockWorkload} />, { wrapper });

    expect(screen.getByTestId('is-fetching')).toHaveTextContent('true');
  });

  it('shows not fetching state correctly', () => {
    mockUseIsFetching.mockReturnValue(0);

    render(<InferenceMetrics workload={mockWorkload} />, { wrapper });

    expect(screen.getByTestId('is-fetching')).toHaveTextContent('false');
  });

  it('handles charts refresh correctly', () => {
    render(<InferenceMetrics workload={mockWorkload} />, { wrapper });

    const refreshButton = screen.getByTestId('refresh-button');
    fireEvent.click(refreshButton);

    expect(mockInvalidateQueries).toHaveBeenCalledWith({
      queryKey: [
        'project',
        'test-project-id',
        'workload',
        'workload-1',
        'metrics',
      ],
    });
  });

  it('handles refresh when time range has changed', () => {
    // Test that the component can handle refreshes
    // Since we already mocked getCurrentTimeRange globally, this test verifies
    // that the refresh functionality works without causing errors
    render(<InferenceMetrics workload={mockWorkload} />, { wrapper });

    const refreshButton = screen.getByTestId('refresh-button');

    // Should not throw when refresh is called
    expect(() => fireEvent.click(refreshButton)).not.toThrow();

    // The component should still be rendered
    expect(
      screen.getByText('details.sections.inferenceMetrics'),
    ).toBeInTheDocument();
  });

  it('updates last fetched timestamp when not fetching', () => {
    // Mock the current date for consistent testing
    const mockDate = new Date('2022-01-01T00:00:00.000Z');
    vi.setSystemTime(mockDate);

    mockUseIsFetching.mockReturnValue(0);

    render(<InferenceMetrics workload={mockWorkload} />, { wrapper });

    // The last fetched timestamp should be set
    expect(screen.getByTestId('last-fetched')).toHaveTextContent(
      '2022-01-01T00:00:00.000Z',
    );
  });

  it('invalidates queries when time range changes', () => {
    render(<InferenceMetrics workload={mockWorkload} />, { wrapper });

    const timeRangeButton = screen.getByTestId('time-range-button');
    fireEvent.click(timeRangeButton);

    expect(mockInvalidateQueries).toHaveBeenCalledWith({
      queryKey: [
        'project',
        'test-project-id',
        'workload',
        'workload-1',
        'metrics',
      ],
    });
  });

  it('handles different workload types', () => {
    const trainingWorkload: Workload = {
      ...mockWorkload,
      type: WorkloadType.FINE_TUNING,
    };

    render(<InferenceMetrics workload={trainingWorkload} />, { wrapper });

    // Component should still render but the metric cards will handle the workload type internally
    expect(
      screen.getByText('details.sections.inferenceMetrics'),
    ).toBeInTheDocument();
    expect(screen.getByTestId('time-to-first-token-card')).toBeInTheDocument();
  });

  it('handles different workload statuses', () => {
    const stoppedWorkload: Workload = {
      ...mockWorkload,
      status: WorkloadStatus.TERMINATED,
    };

    render(<InferenceMetrics workload={stoppedWorkload} />, { wrapper });

    // Component should still render but the metric cards will handle the workload status internally
    expect(
      screen.getByText('details.sections.inferenceMetrics'),
    ).toBeInTheDocument();
    expect(screen.getByTestId('time-to-first-token-card')).toBeInTheDocument();
  });
});
