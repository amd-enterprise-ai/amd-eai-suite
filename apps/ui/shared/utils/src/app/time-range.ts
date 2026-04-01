// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { TimeRangePeriod } from '@amdenterpriseai/types';

const MINUTE_MS = 60 * 1000;
const HOUR_MS = 60 * MINUTE_MS;
const DAY_MS = 24 * HOUR_MS;

export const getCurrentTimeRange = (period: TimeRangePeriod) => {
  let start: Date, end: Date;
  const now = new Date();

  end = new Date(now.getTime());

  if (period === TimeRangePeriod['24H']) {
    start = new Date(end.getTime() - DAY_MS);
  } else if (period === TimeRangePeriod['7D']) {
    start = new Date(end.getTime() - 7 * DAY_MS);
  } else if (period === TimeRangePeriod['15M']) {
    start = new Date(end.getTime() - 15 * MINUTE_MS);
  } else if (period === TimeRangePeriod['30M']) {
    start = new Date(end.getTime() - 30 * MINUTE_MS);
  } else {
    start = new Date(end.getTime() - HOUR_MS);
  }

  return { start, end };
};
