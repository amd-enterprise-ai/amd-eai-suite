// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { TimeRangePeriod } from '@/types/enums/metrics';

export const getCurrentTimeRange = (period: TimeRangePeriod) => {
  let start: Date, end: Date;
  const now = new Date();

  if (period === TimeRangePeriod['24H'] || period === TimeRangePeriod['7D']) {
    end = new Date(
      Math.ceil(now.getTime() / (15 * 60 * 1000)) * (15 * 60 * 1000),
    );
  } else {
    end = new Date(Math.ceil(now.getTime() / (60 * 1000)) * (60 * 1000));
  }

  if (period === TimeRangePeriod['24H']) {
    start = new Date(end.getTime() - 24 * 60 * 60 * 1000);
  } else if (period === TimeRangePeriod['7D']) {
    start = new Date(end.getTime() - 7 * 24 * 60 * 60 * 1000);
  } else {
    start = new Date(end.getTime() - 60 * 60 * 1000);
  }

  return { start, end };
};
