// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  AvailableChartColorsKeys,
  chartColors,
  ColorUtility,
} from '@amdenterpriseai/types';

// Tremor Raw chartColors [v0.1.0]

export const AvailableChartColors: AvailableChartColorsKeys[] = Object.keys(
  chartColors,
) as Array<AvailableChartColorsKeys>;

export const constructCategoryColors = (
  categories: string[],
  colors: AvailableChartColorsKeys[],
): Map<string, AvailableChartColorsKeys> => {
  const categoryColors = new Map<string, AvailableChartColorsKeys>();
  categories.forEach((category, index) => {
    categoryColors.set(category, colors[index % colors.length]);
  });
  return categoryColors;
};

export const getColorClassName = (
  color: AvailableChartColorsKeys,
  type: ColorUtility,
): string => {
  const fallbackColor = {
    bg: 'bg-gray-500',
    stroke: 'stroke-gray-500',
    fill: 'fill-gray-500',
    text: 'text-gray-500',
  };
  return chartColors[color]?.[type] ?? fallbackColor[type];
};

// Tremor Raw getYAxisDomain [v0.0.0]

export const getYAxisDomain = (
  autoMinValue: boolean,
  minValue: number | undefined,
  maxValue: number | undefined,
) => {
  const minDomain = autoMinValue ? 'auto' : (minValue ?? 0);
  const maxDomain = maxValue ?? 'auto';
  return [minDomain, maxDomain];
};

/**
 * Returns the smallest "nice" max value that is ≥ dataMax and divides evenly
 * into (tickCount - 1) equal intervals, so a Y-axis starting at 0 always has
 * exactly tickCount linearly-spaced ticks regardless of the data's magnitude.
 *
 * Step sizes follow the 1 → 2 → 5 × 10ⁿ series (same as d3-scale's nice()),
 * so results are always human-readable round numbers at any scale (MHz, bytes,
 * counts, etc.).
 *
 * @example
 * computeLinearChartMax(2107, 6)    // → 2500  (ticks: 0,500,1000,1500,2000,2500)
 * computeLinearChartMax(1_700_000, 6) // → 2_500_000
 * computeLinearChartMax(0.0042, 6)  // → 0.005
 */
export function computeLinearChartMax(
  dataMax: number,
  tickCount: number,
): number {
  if (dataMax <= 0 || tickCount < 2) return tickCount < 2 ? 1 : 100;
  const intervals = tickCount - 1;
  const rawStep = dataMax / intervals;
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
  const normalized = rawStep / magnitude;
  let niceStep: number;
  if (normalized <= 1) niceStep = magnitude;
  else if (normalized <= 2) niceStep = 2 * magnitude;
  else if (normalized <= 5) niceStep = 5 * magnitude;
  else niceStep = 10 * magnitude;
  return niceStep * intervals;
}

// Tremor Raw hasOnlyOneValueForKey [v0.1.0]

export function hasOnlyOneValueForKey(
  array: any[],
  keyToCheck: string,
): boolean {
  const val: any[] = [];

  for (const obj of array) {
    if (Object.hasOwn(obj, keyToCheck)) {
      val.push(obj[keyToCheck]);
      if (val.length > 1) {
        return false;
      }
    }
  }

  return true;
}
