// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { getLatestDate } from '@/utils/app/date';

describe('getLatestDate', () => {
  it('returns undefined for an empty array', () => {
    expect(getLatestDate([])).toBeUndefined();
  });

  it('returns the only date in a single-element array', () => {
    const date = new Date('2023-01-01T00:00:00Z');
    expect(getLatestDate([date])).toEqual(date);
  });

  it('returns the latest date from multiple dates', () => {
    const d1 = new Date('2022-01-01T00:00:00Z');
    const d2 = new Date('2023-01-01T00:00:00Z');
    const d3 = new Date('2021-01-01T00:00:00Z');
    const result = getLatestDate([d1, d2, d3]);
    expect(result?.getTime()).toBe(d2.getTime());
  });

  it('handles dates with the same value', () => {
    const d1 = new Date('2023-01-01T00:00:00Z');
    const d2 = new Date('2023-01-01T00:00:00Z');
    expect(getLatestDate([d1, d2])).toEqual(d1);
  });

  it('does not mutate the input array', () => {
    const dates = [
      new Date('2022-01-01T00:00:00Z'),
      new Date('2023-01-01T00:00:00Z'),
    ];
    const original = [...dates];
    getLatestDate(dates);
    expect(dates).toEqual(original);
  });
});
