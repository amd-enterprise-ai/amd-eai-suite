// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getCurrentTimeRange } from '@/utils/app/time-range';

import { TimeRangePeriod } from '@/types/enums/metrics';

describe('getCurrentTimeRange', () => {
  const mockDate = new Date('2023-01-01T12:00:00Z');
  const fifteenMinutes = 15 * 60 * 1000;
  const oneHour = 60 * 60 * 1000;
  const oneDay = 24 * 60 * 60 * 1000;
  const sevenDays = 7 * oneDay;

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(mockDate);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should calculate the correct time range for 24H period', () => {
    const { start, end } = getCurrentTimeRange(TimeRangePeriod['24H']);

    expect(end.getTime()).toBe(
      Math.ceil(mockDate.getTime() / fifteenMinutes) * fifteenMinutes,
    );
    expect(start.getTime()).toBe(end.getTime() - oneDay);
  });

  it('should calculate the correct time range for 7D period', () => {
    const { start, end } = getCurrentTimeRange(TimeRangePeriod['7D']);

    expect(end.getTime()).toBe(
      Math.ceil(mockDate.getTime() / fifteenMinutes) * fifteenMinutes,
    );
    expect(start.getTime()).toBe(end.getTime() - sevenDays);
  });

  it('should calculate the correct time range for other periods', () => {
    // @ts-ignore
    const { start, end } = getCurrentTimeRange('OTHER');

    expect(end.getTime()).toBe(
      Math.ceil(mockDate.getTime() / oneHour) * oneHour,
    );
    expect(start.getTime()).toBe(end.getTime() - oneHour);
  });
});
