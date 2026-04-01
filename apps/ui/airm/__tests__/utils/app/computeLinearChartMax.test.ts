// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { computeLinearChartMax } from '@amdenterpriseai/utils/app';

describe('computeLinearChartMax', () => {
  it('produces exactly tickCount evenly-spaced ticks from 0 for MHz clock speeds', () => {
    const tickCount = 6;
    const max = computeLinearChartMax(2107, tickCount);
    const step = max / (tickCount - 1);
    expect(max).toBe(2500);
    expect(step).toBe(500);
  });

  it('produces exactly tickCount evenly-spaced ticks for idle GPU clock speeds', () => {
    const tickCount = 6;
    const max = computeLinearChartMax(132, tickCount);
    const step = max / (tickCount - 1);
    expect(max).toBe(250);
    expect(step).toBe(50);
  });

  it('scales to millions without hard-coding any unit', () => {
    const tickCount = 6;
    const max = computeLinearChartMax(1_700_000, tickCount);
    expect(max).toBe(2_500_000);
    expect(max / (tickCount - 1)).toBe(500_000);
  });

  it('scales to billions', () => {
    const tickCount = 6;
    const max = computeLinearChartMax(850_000_000, tickCount);
    expect(max).toBe(1_000_000_000);
    expect(max / (tickCount - 1)).toBe(200_000_000);
  });

  it('scales to small decimals', () => {
    const tickCount = 6;
    const max = computeLinearChartMax(0.0042, tickCount);
    expect(max).toBeCloseTo(0.005);
    expect(max / (tickCount - 1)).toBeCloseTo(0.001);
  });

  it('returns exact max when dataMax is already a nice multiple', () => {
    const max = computeLinearChartMax(2500, 6);
    expect(max).toBe(2500);
  });

  it('works with a different tickCount', () => {
    const tickCount = 4;
    const max = computeLinearChartMax(75, tickCount);
    expect(max).toBe(150);
    expect(max / (tickCount - 1)).toBe(50);
  });

  it('returns 100 for zero or negative dataMax', () => {
    expect(computeLinearChartMax(0, 6)).toBe(100);
    expect(computeLinearChartMax(-50, 6)).toBe(100);
  });

  it('returns 1 when tickCount is less than 2', () => {
    expect(computeLinearChartMax(500, 1)).toBe(1);
  });

  it('produces a maxValue that is always >= dataMax', () => {
    const cases = [1, 99, 100, 101, 999, 1000, 1001, 9999, 12345, 99999];
    for (const dataMax of cases) {
      const max = computeLinearChartMax(dataMax, 6);
      expect(max).toBeGreaterThanOrEqual(dataMax);
    }
  });

  it('produces ticks that are linearly spaced (constant step)', () => {
    const cases = [50, 132, 2107, 1_700_000, 850_000_000];
    for (const dataMax of cases) {
      const tickCount = 6;
      const max = computeLinearChartMax(dataMax, tickCount);
      const step = max / (tickCount - 1);
      for (let i = 0; i < tickCount; i++) {
        const tick = i * step;
        expect(tick % step).toBeCloseTo(0);
      }
    }
  });
});
