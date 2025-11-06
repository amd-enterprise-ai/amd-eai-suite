// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { millicoresToCpus } from '@/utils/app/cpu';

import { describe, expect, it } from 'vitest';

describe('cpu utils', () => {
  describe('millicoresToCpus', () => {
    it('should convert millicores to CPUs', () => {
      expect(millicoresToCpus(1000)).toBe(1);
    });

    it('should handle zero millicores', () => {
      expect(millicoresToCpus(0)).toBe(0);
    });

    it('should handle fractional millicores', () => {
      expect(millicoresToCpus(500)).toBe(0.5);
    });

    it('should handle large values', () => {
      expect(millicoresToCpus(4000)).toBe(4);
    });

    it('should handle decimal precision correctly', () => {
      expect(millicoresToCpus(1234)).toBe(1.234);
    });

    it('should handle very small values', () => {
      expect(millicoresToCpus(1)).toBe(0.001);
    });

    it('should handle negative values', () => {
      expect(millicoresToCpus(-500)).toBe(-0.5);
    });

    it('should handle values requiring rounding', () => {
      expect(millicoresToCpus(1234.5678)).toBe(1.235);
    });
  });
});
