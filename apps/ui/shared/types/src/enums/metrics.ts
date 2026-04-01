// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export enum TimeRangePeriod {
  '15M' = '15m',
  '30M' = '30m',
  '1H' = '1h',
  '24H' = '24h',
  '7D' = '7d',
}

/** Default periods for chart time selector (1h, 24h, 7d). Override with `periods` prop for 15m/30m. */
export const DEFAULT_CHART_TIME_PERIODS: TimeRangePeriod[] = [
  TimeRangePeriod['1H'],
  TimeRangePeriod['24H'],
  TimeRangePeriod['7D'],
];
