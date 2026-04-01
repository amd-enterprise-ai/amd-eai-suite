// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { LogLevel } from '@amdenterpriseai/types';

export const LOG_LEVEL_COLORS: Record<LogLevel, string> = {
  [LogLevel.TRACE]: '#999999',
  [LogLevel.DEBUG]: '#666666',
  [LogLevel.INFO]: '#11a8cd',
  [LogLevel.WARNING]: '#e5e510',
  [LogLevel.ERROR]: '#f14c4c',
  [LogLevel.CRITICAL]: '#ff0000',
  [LogLevel.UNKNOWN]: '#666666',
};

export const getLogLevelColor = (level: LogLevel): string => {
  return LOG_LEVEL_COLORS[level] || LOG_LEVEL_COLORS[LogLevel.UNKNOWN];
};
