// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  convertStringToNumber,
  displayFixedNumber,
  displayHumanReadableBytes,
  displayHumanReadableMegaBytes,
  displayTimestamp,
  formatDurationFromSeconds,
  searchPatternInValue,
  toCamelCase,
} from '@/utils/app/strings';

import { format } from 'date-fns';
import { describe, expect, it } from 'vitest';

describe('toCamelCase', () => {
  it('should convert kebab-case to camelCase', () => {
    expect(toCamelCase('kebab-case-string')).toBe('kebabCaseString');
  });

  it('should convert snake_case to camelCase', () => {
    expect(toCamelCase('snake_case_string')).toBe('snakeCaseString');
  });

  it('should handle mixed delimiters', () => {
    expect(toCamelCase('mixed-delimiters_string')).toBe(
      'mixedDelimitersString',
    );
  });

  it('should handle uppercase letters', () => {
    expect(toCamelCase('UpperCase-String')).toBe('uppercaseString');
  });

  it('should handle empty string', () => {
    expect(toCamelCase('')).toBe('');
  });

  it('should handle string with no delimiters', () => {
    expect(toCamelCase('nodelimiters')).toBe('nodelimiters');
  });
});

describe('displayFixedFloat', () => {
  it('should format number with default decimals', () => {
    expect(displayFixedNumber(123.456)).toBe('123.46');
  });

  it('should format number with specified decimals', () => {
    expect(displayFixedNumber(123.456, 1)).toBe('123.5');
  });

  it('should remove trailing .00', () => {
    expect(displayFixedNumber(123.0)).toBe('123');
  });

  it('should handle zero value', () => {
    expect(displayFixedNumber(0)).toBe('0');
  });

  it('should handle negative numbers', () => {
    expect(displayFixedNumber(-123.456)).toBe('-123.46');
  });

  it('should handle large numbers', () => {
    expect(displayFixedNumber(123456789.123456)).toBe('123456789.12');
  });
});

describe('displayTimestamp', () => {
  it('should format a valid Date object', () => {
    const date = new Date('2023-01-01T12:34:56');
    const result = displayTimestamp(date);
    expect(result).toContain(format(date, 'yyyy/MM/dd HH:mm'));
  });

  it('should throw error for non-Date input', () => {
    expect(() => displayTimestamp('2023-01-01' as any)).toThrow(
      'Invalid date object',
    );
    expect(() => displayTimestamp(123456 as any)).toThrow(
      'Invalid date object',
    );
    expect(() => displayTimestamp(null as any)).toThrow('Invalid date object');
    expect(() => displayTimestamp(undefined as any)).toThrow(
      'Invalid date object',
    );
  });

  describe('formatDurationFromSeconds', () => {
    it('returns only seconds for values under a minute', () => {
      expect(formatDurationFromSeconds(0)).toBe('0s');
      expect(formatDurationFromSeconds(0.5)).toBe('0s');
      expect(formatDurationFromSeconds(15)).toBe('15s');
      expect(formatDurationFromSeconds(59)).toBe('59s');
    });

    it('returns minutes and seconds for values under an hour', () => {
      expect(formatDurationFromSeconds(60)).toBe('1m');
      expect(formatDurationFromSeconds(125)).toBe('2m 5s');
      expect(formatDurationFromSeconds(3599)).toBe('59m 59s');
    });

    it('returns hours and minutes for values over an hour', () => {
      expect(formatDurationFromSeconds(3600)).toBe('1h');
      expect(formatDurationFromSeconds(3723)).toBe('1h 2m');
      expect(formatDurationFromSeconds(7325)).toBe('2h 2m');
    });

    it('returns months and weeks for values over a month', () => {
      // Roughly 1 month = 2629800 seconds (~30.44 days)
      expect(formatDurationFromSeconds(2629800)).toBe('30d 10h');
      expect(formatDurationFromSeconds(3024000)).toBe('1mo 4d');
      expect(formatDurationFromSeconds(3888000)).toBe('1mo 14d');
    });

    it('returns years and months for values over a year', () => {
      // 1 year = 31556952 seconds (365.24 days)
      expect(formatDurationFromSeconds(31556952)).toBe('1yr 5h');
      expect(formatDurationFromSeconds(34214400)).toBe('1yr 1mo');
      expect(formatDurationFromSeconds(39312000)).toBe('1yr 3mo');
    });

    it('handles exact boundary cases correctly', () => {
      expect(formatDurationFromSeconds(60)).toBe('1m'); // 1 minute
      expect(formatDurationFromSeconds(3600)).toBe('1h'); // 1 hour
      expect(formatDurationFromSeconds(3661)).toBe('1h 1m'); // 1:01:01
    });
  });
});

describe('convertStringToNumber', () => {
  it('should convert string to number', () => {
    expect(convertStringToNumber('123')).toBe(123);
  });

  it('should handle negative string numbers', () => {
    expect(convertStringToNumber('-456')).toBe(-456);
  });

  it('should handle string with leading zeros', () => {
    expect(convertStringToNumber('007')).toBe(7);
  });

  it('should handle empty string', () => {
    expect(convertStringToNumber('')).toBeNaN();
  });

  it('should handle non-numeric string', () => {
    expect(convertStringToNumber('abc')).toBeNaN();
  });

  it('should return the same value if already a number', () => {
    expect(convertStringToNumber(42 as any)).toBe(42);
  });
});

describe('displayHumanReadableMegaBytes', () => {
  it('should convert megabytes to human readable format', () => {
    expect(displayHumanReadableMegaBytes(1)).toBe('1.00 MB');
  });

  it('should handle zero megabytes', () => {
    expect(displayHumanReadableMegaBytes(0)).toBe('0 Bytes');
  });

  it('should convert large megabyte values to GB', () => {
    expect(displayHumanReadableMegaBytes(1024)).toBe('1.00 GB');
  });

  it('should handle fractional megabytes', () => {
    expect(displayHumanReadableMegaBytes(0.5)).toBe('512.00 KB');
  });
});

describe('displayHumanReadableBytes', () => {
  it('should handle zero bytes', () => {
    expect(displayHumanReadableBytes(0)).toBe('0 Bytes');
  });

  it('should handle bytes', () => {
    expect(displayHumanReadableBytes(512)).toBe('512.00 B');
  });

  it('should convert to KB', () => {
    expect(displayHumanReadableBytes(1024)).toBe('1.00 KB');
  });

  it('should convert to MB', () => {
    expect(displayHumanReadableBytes(1048576)).toBe('1.00 MB');
  });

  it('should convert to GB', () => {
    expect(displayHumanReadableBytes(1073741824)).toBe('1.00 GB');
  });

  it('should convert to TB', () => {
    expect(displayHumanReadableBytes(1099511627776)).toBe('1.00 TB');
  });

  it('should convert to PB', () => {
    expect(displayHumanReadableBytes(1125899906842624)).toBe('1.00 PB');
  });

  it('should handle negative numbers', () => {
    expect(displayHumanReadableBytes(-1024)).toBe('0 GB');
  });

  it('should handle NaN', () => {
    expect(displayHumanReadableBytes(NaN)).toBe('0 GB');
  });

  it('should handle very large numbers', () => {
    expect(displayHumanReadableBytes(Number.MAX_SAFE_INTEGER)).toBe('8.00 PB');
  });

  it('should format with proper decimals', () => {
    expect(displayHumanReadableBytes(1536)).toBe('1.50 KB');
  });
});

describe('searchPatternInValue', () => {
  it('should find pattern in string value', () => {
    expect(searchPatternInValue('Hello World', 'hello')).toBe(true);
  });

  it('should be case insensitive', () => {
    expect(searchPatternInValue('Hello World', 'WORLD')).toBe(true);
  });

  it('should return false if pattern not found', () => {
    expect(searchPatternInValue('Hello World', 'xyz')).toBe(false);
  });

  it('should handle undefined value', () => {
    expect(searchPatternInValue(undefined, 'test')).toBe(false);
  });

  it('should handle null value', () => {
    expect(searchPatternInValue(null, 'test')).toBe(false);
  });

  it('should handle number values', () => {
    expect(searchPatternInValue(123, '12')).toBe(true);
  });

  it('should handle boolean values', () => {
    expect(searchPatternInValue(true, 'true')).toBe(true);
  });

  it('should handle empty pattern', () => {
    expect(searchPatternInValue('test', '')).toBe(true);
  });

  it('should handle empty value with pattern', () => {
    expect(searchPatternInValue('', 'test')).toBe(false);
  });
});
