// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, fireEvent, render, screen } from '@testing-library/react';

import { getCurrentTimeRange } from '@amdenterpriseai/utils/app';

import { TimeRangePeriod } from '@amdenterpriseai/types';

import { ChartTimeSelector } from '@amdenterpriseai/components';

import { vi } from 'vitest';

vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations = {
        'timeRange.description': 'Select time range',
        'timeRange.range.15m': '15 min',
        'timeRange.range.30m': '30 min',
        'timeRange.range.1h': '1 Hour',
        'timeRange.range.24h': '24 Hours',
        'timeRange.range.7d': '7 Days',
      };
      return key in translations
        ? translations[key as keyof typeof translations]
        : key;
    },
  }),
}));

vi.mock('@amdenterpriseai/utils/app', async (importOriginal) => ({
  ...(await importOriginal<any>()),
  getCurrentTimeRange: vi.fn((period: TimeRangePeriod) => {
    const mockTimeRanges = {
      [TimeRangePeriod['15M']]: {
        start: new Date('2023-01-01T12:45:00Z'),
        end: new Date('2023-01-01T13:00:00Z'),
      },
      [TimeRangePeriod['30M']]: {
        start: new Date('2023-01-01T12:30:00Z'),
        end: new Date('2023-01-01T13:00:00Z'),
      },
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
    expect(tabs).toHaveLength(3);
    expect(tabs[0]).toBeInTheDocument();
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
    // Order: 1H, 24H, 7D -> 24H is index 1
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
    const order = [
      TimeRangePeriod['1H'],
      TimeRangePeriod['24H'],
      TimeRangePeriod['7D'],
    ];
    order.forEach((period, index) => {
      act(() => {
        fireEvent.click(tabs[index]);
      });
      expect(getCurrentTimeRange).toHaveBeenCalledWith(period);
      expect(onTimeRangeChangeMock).toHaveBeenCalledWith(
        period,
        getCurrentTimeRange(period),
      );
    });
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
