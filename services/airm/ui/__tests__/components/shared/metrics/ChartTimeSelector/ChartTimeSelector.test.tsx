// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, fireEvent, render, screen } from '@testing-library/react';

import { getCurrentTimeRange } from '@/utils/app/time-range';

import { TimeRangePeriod } from '@/types/enums/metrics';

import { ChartTimeSelector } from '@/components/shared/Metrics/ChartTimeSelector';

import { vi } from 'vitest';

vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations = {
        'timeRange.description': 'Select time range',
        'timeRange.range.1H': '1 Hour',
        'timeRange.range.24H': '24 Hours',
        'timeRange.range.7D': '7 Days',
      };
      return key in translations
        ? translations[key as keyof typeof translations]
        : key;
    },
  }),
}));

vi.mock('@/utils/app/time-range', () => ({
  getCurrentTimeRange: vi.fn((period: TimeRangePeriod) => {
    const mockTimeRanges = {
      [TimeRangePeriod['1H']]: {
        start: new Date('2023-01-01T12:00:00Z'),
        end: new Date('2023-01-01T13:00:00Z'),
      },
      [TimeRangePeriod['24H']]: {
        start: new Date('2022-12-31T13:00:00Z'),
        end: new Date('2023-01-01T13:00:00Z'),
      },
      [TimeRangePeriod['7D']]: {
        start: new Date('2022-12-25T13:00:00Z'),
        end: new Date('2023-01-01T13:00:00Z'),
      },
    };
    return mockTimeRanges[period];
  }),
}));

describe('ChartTimeSelector', () => {
  it('renders all time range tabs with correct translations', () => {
    act(() => {
      render(
        <ChartTimeSelector
          onTimeRangeChange={() => {}}
          initialTimePeriod={TimeRangePeriod['1H']}
          onChartsRefresh={() => {}}
          isFetching={false}
        />,
      );
    });
    const tabs = screen.getAllByRole('tab');
    expect(tabs[0]).toBeInTheDocument();
    expect(tabs[1]).toBeInTheDocument();
    expect(tabs[2]).toBeInTheDocument();
  });

  it('sets initial time period correctly', () => {
    act(() => {
      render(
        <ChartTimeSelector
          onTimeRangeChange={() => {}}
          initialTimePeriod={TimeRangePeriod['24H']}
          onChartsRefresh={() => {}}
          isFetching={false}
        />,
      );
    });

    const tabs = screen.getAllByRole('tab');

    expect(tabs[1]).toHaveAttribute('aria-selected', 'true');
  });

  it('calls onTimeRangeChange with correct time range when changing tabs', () => {
    const onTimeRangeChangeMock = vi.fn();

    act(() => {
      render(
        <ChartTimeSelector
          onTimeRangeChange={onTimeRangeChangeMock}
          initialTimePeriod={TimeRangePeriod['1H']}
          onChartsRefresh={() => {}}
          isFetching={false}
        />,
      );
    });

    const tabs = screen.getAllByRole('tab');

    const tab24h = tabs[1];
    act(() => {
      fireEvent.click(tab24h);
    });

    const expectedTimeRange = getCurrentTimeRange(TimeRangePeriod['24H']);
    expect(onTimeRangeChangeMock).toHaveBeenCalledWith(
      TimeRangePeriod['24H'],
      expectedTimeRange,
    );
  });

  it('handles all available time periods correctly', () => {
    const onTimeRangeChangeMock = vi.fn();

    act(() => {
      render(
        <ChartTimeSelector
          onTimeRangeChange={onTimeRangeChangeMock}
          initialTimePeriod={TimeRangePeriod['1H']}
          onChartsRefresh={() => {}}
          isFetching={false}
        />,
      );
    });

    const tabs = screen.getAllByRole('tab');

    act(() => {
      fireEvent.click(tabs[0]);
    });
    expect(getCurrentTimeRange).toHaveBeenCalledWith(TimeRangePeriod['1H']);
    expect(onTimeRangeChangeMock).toHaveBeenCalledWith(
      TimeRangePeriod['1H'],
      getCurrentTimeRange(TimeRangePeriod['1H']),
    );

    act(() => {
      fireEvent.click(tabs[1]);
    });
    expect(getCurrentTimeRange).toHaveBeenCalledWith(TimeRangePeriod['24H']);
    expect(onTimeRangeChangeMock).toHaveBeenCalledWith(
      TimeRangePeriod['24H'],
      getCurrentTimeRange(TimeRangePeriod['24H']),
    );

    act(() => {
      fireEvent.click(tabs[2]);
    });
    expect(getCurrentTimeRange).toHaveBeenCalledWith(TimeRangePeriod['7D']);
    expect(onTimeRangeChangeMock).toHaveBeenCalledWith(
      TimeRangePeriod['7D'],
      getCurrentTimeRange(TimeRangePeriod['7D']),
    );
  });

  it('renders last updated timestamp when lastFetchedTimestamp is provided', () => {
    const lastFetchedTimestamp = new Date('2023-01-01T14:00:00Z');
    act(() => {
      render(
        <ChartTimeSelector
          onTimeRangeChange={() => {}}
          initialTimePeriod={TimeRangePeriod['1H']}
          onChartsRefresh={() => {}}
          isFetching={false}
          lastFetchedTimestamp={lastFetchedTimestamp}
        />,
      );
    });
    expect(screen.getByText(/data.lastUpdated/i)).toBeInTheDocument();
  });
});
