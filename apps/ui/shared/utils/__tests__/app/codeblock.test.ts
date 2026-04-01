// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  programmingLanguages,
  generateRandomString,
} from '@amdenterpriseai/utils/app';

describe('programmingLanguages', () => {
  it('should contain common programming language mappings', () => {
    expect(programmingLanguages['javascript']).toBe('.js');
    expect(programmingLanguages['python']).toBe('.py');
    expect(programmingLanguages['typescript']).toBe('.ts');
    expect(programmingLanguages['java']).toBe('.java');
    expect(programmingLanguages['go']).toBe('.go');
  });

  it('should handle C++ variations', () => {
    expect(programmingLanguages['cpp']).toBe('.cpp');
    expect(programmingLanguages['c++']).toBe('.cpp');
  });

  it('should include web languages', () => {
    expect(programmingLanguages['html']).toBe('.html');
    expect(programmingLanguages['css']).toBe('.css');
  });

  it('should return undefined for unknown languages', () => {
    expect(programmingLanguages['unknown-language']).toBeUndefined();
  });
});

describe('generateRandomString', () => {
  it('should generate string of specified length', () => {
    const length = 10;
    const result = generateRandomString(length);
    expect(result).toHaveLength(length);
  });

  it('should generate uppercase string by default', () => {
    const result = generateRandomString(10);
    expect(result).toMatch(/^[ABCDEFGHJKLMNPQRSTUVWXY3456789]+$/);
  });

  it('should generate lowercase string when specified', () => {
    const result = generateRandomString(10, true);
    expect(result).toMatch(/^[abcdefghjklmnpqrstuvwxy3456789]+$/);
  });

  it('should not contain similar looking characters', () => {
    // Run multiple times to increase confidence
    for (let i = 0; i < 100; i++) {
      const result = generateRandomString(50);
      expect(result).not.toMatch(/[Z210IO]/);
    }
  });

  it('should generate different strings on consecutive calls', () => {
    const result1 = generateRandomString(20);
    const result2 = generateRandomString(20);
    expect(result1).not.toBe(result2);
  });

  it('should handle length of 0', () => {
    const result = generateRandomString(0);
    expect(result).toBe('');
  });

  it('should handle length of 1', () => {
    const result = generateRandomString(1);
    expect(result).toHaveLength(1);
  });

  it('should use seeded randomness consistently', () => {
    // Mock Math.random to return predictable values
    const mockRandom = vi.spyOn(Math, 'random');
    mockRandom.mockReturnValueOnce(0);
    mockRandom.mockReturnValueOnce(0.5);
    mockRandom.mockReturnValueOnce(0.99);

    const result = generateRandomString(3);
    expect(result).toHaveLength(3);

    mockRandom.mockRestore();
  });
});
