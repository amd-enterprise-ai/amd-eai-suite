// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Duration,
  Locale,
  addSeconds,
  format,
  formatDuration,
  intervalToDuration,
} from 'date-fns';

import { displayBytesInGigabytes } from './memory';
import { millicoresToCpus } from './cpu';

const shortLocale: Pick<Locale, 'formatDistance'> = {
  formatDistance: (token: string, count: number): string => {
    const shortTokens: Record<string, string> = {
      xSeconds: `${count}s`,
      xMinutes: `${count}m`,
      xHours: `${count}h`,
      xDays: `${count}d`,
      xMonths: `${count}mo`,
      xYears: `${count}yr`,
    };
    return shortTokens[token] ?? `${count} ${token}`;
  },
};

export const toCamelCase = (str: string): string => {
  return str.toLowerCase().replace(/[-_](.)/g, (_, char) => char.toUpperCase());
};

export const displayPercentage = (percentage: number): string => {
  return `${+percentage.toFixed(2)}%`;
};

export const displayFixedNumber = (value: number, decimals = 2): string => {
  return `${+value.toFixed(decimals)}`;
};

export const convertStringToNumber = (val: string): number => {
  if (typeof val === 'string') return parseInt(val, 10);
  return val;
};

export const displayTimestamp = (timestamp: Date): string => {
  if (!(timestamp instanceof Date)) {
    throw new Error('Invalid date object');
  }
  return format(timestamp, 'yyyy/MM/dd HH:mm');
};

export const displayHumanReadableMegaBytes = (megaBytes: number): string => {
  return displayHumanReadableBytes(megaBytes * 1024 ** 2);
};

export const formatDurationFromSeconds = (inputSeconds: number): string => {
  const now = new Date(Date.UTC(1970, 0, 0, 0, 0, 0));
  const future = addSeconds(now, inputSeconds);
  const duration = intervalToDuration({ start: now, end: future });

  const orderedUnits = [
    'years',
    'months',
    'days',
    'hours',
    'minutes',
    'seconds',
  ] as (keyof Duration)[];

  // Find the first two units with non-zero values
  const formatUnits = orderedUnits
    .filter((unit) => duration[unit] && duration[unit] > 0)
    .slice(0, 2);

  if (formatUnits.length === 0) return '0s';

  return formatDuration(duration, { format: formatUnits, locale: shortLocale });
};

export const displayHumanReadableBytes = (bytes: number): string => {
  if (isNaN(bytes) || bytes < 0) return '0 GB';
  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  if (bytes === 0) return '0 Bytes';
  const i = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  );
  const value = bytes / 1024 ** i;
  return `${value.toFixed(2)} ${units[i]}`;
};

export const searchPatternInValue = (
  val: unknown | undefined,
  pattern: string,
) =>
  String(val ?? '')
    .toLowerCase()
    .includes(pattern.toLowerCase());

export const formatGpuAllocation = (
  count: number,
  percentage: number,
): string => {
  return `${count} (${displayPercentage(percentage)})`;
};

export const formatCpuAllocation = (
  milliCores: number,
  percentage: number,
): string => {
  return `${millicoresToCpus(milliCores)} (${displayPercentage(percentage)})`;
};

export const formatMemoryAllocation = (
  bytes: number,
  percentage: number,
): string => {
  return `${displayBytesInGigabytes(bytes)} (${displayPercentage(percentage)})`;
};

export const formatTokens = (tokens: number): string => {
  if (tokens >= 1000000) {
    return `${displayFixedNumber(tokens / 1000)}M`;
  } else if (tokens >= 1000) {
    return `${displayFixedNumber(tokens / 1000)}K`;
  } else {
    return tokens.toString();
  }
};

export const formatSeconds = (seconds: number | string): string => {
  const value = typeof seconds === 'string' ? parseFloat(seconds) : seconds;
  if (value < 1) {
    return `${displayFixedNumber(value * 1000, 0)} ms`;
  } else {
    return `${displayFixedNumber(value)} s`;
  }
};
