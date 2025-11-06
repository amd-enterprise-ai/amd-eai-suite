// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  bytesToGigabytes,
  displayBytesInGigabytes,
  gigabytesToBytes,
} from '@/utils/app/memory';

describe('displayBytesInGigabytes', () => {
  it('should display bytes in gigabytes correctly', () => {
    expect(displayBytesInGigabytes(1 * 1024 * 1024 * 1024)).toBe('1 GB');
    expect(displayBytesInGigabytes(2 * 1024 * 1024 * 1024)).toBe('2 GB');
    expect(displayBytesInGigabytes(0.5 * 1024 * 1024 * 1024)).toBe('0.5 GB');
    expect(displayBytesInGigabytes(0.255 * 1024 * 1024 * 1024)).toBe('0.26 GB');
  });

  describe('bytesToGigabytes', () => {
    it('should convert bytes to gigabytes correctly', () => {
      expect(bytesToGigabytes(1 * 1024 * 1024 * 1024)).toBe(1);
      expect(bytesToGigabytes(2 * 1024 * 1024 * 1024)).toBe(2);
      expect(bytesToGigabytes(0.5 * 1024 * 1024 * 1024)).toBe(0.5);
    });
  });

  describe('gigabytesToBytes', () => {
    it('should convert gigabytes to bytes correctly', () => {
      expect(gigabytesToBytes(1)).toBe(1 * 1024 * 1024 * 1024);
      expect(gigabytesToBytes(2)).toBe(2 * 1024 * 1024 * 1024);
      expect(gigabytesToBytes(0.5)).toBe(0.5 * 1024 * 1024 * 1024);
    });
  });

  describe('displayBytesInGigabytes', () => {
    it('should display bytes in gigabytes correctly', () => {
      expect(displayBytesInGigabytes(1 * 1024 * 1024 * 1024)).toBe('1 GB');
      expect(displayBytesInGigabytes(2 * 1024 * 1024 * 1024)).toBe('2 GB');
      expect(displayBytesInGigabytes(0.5 * 1024 * 1024 * 1024)).toBe('0.5 GB');
      expect(displayBytesInGigabytes(0.255 * 1024 * 1024 * 1024)).toBe(
        '0.26 GB',
      );
    });
  });
});
