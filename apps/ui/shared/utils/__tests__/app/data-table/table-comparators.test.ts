// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { describe, it, expect } from 'vitest';
import { defaultComparator } from '@amdenterpriseai/utils/app';

describe('defaultComparator', () => {
  it('should compare string values alphabetically', () => {
    const compareFn = defaultComparator<{ name: string }, 'name'>('name');
    const a = { name: 'Alice' };
    const b = { name: 'Bob' };

    expect(compareFn(a, b)).toBeLessThan(0);
    expect(compareFn(b, a)).toBeGreaterThan(0);
  });

  it('should return 0 for equal string values', () => {
    const compareFn = defaultComparator<{ name: string }, 'name'>('name');
    const a = { name: 'Alice' };
    const b = { name: 'Alice' };

    expect(compareFn(a, b)).toBe(0);
  });

  it('should compare numeric values', () => {
    const compareFn = defaultComparator<{ age: number }, 'age'>('age');
    const a = { age: 25 };
    const b = { age: 30 };

    expect(compareFn(a, b)).toBeLessThan(0);
    expect(compareFn(b, a)).toBeGreaterThan(0);
  });

  it('should return 0 for equal numeric values', () => {
    const compareFn = defaultComparator<{ age: number }, 'age'>('age');
    const a = { age: 25 };
    const b = { age: 25 };

    expect(compareFn(a, b)).toBe(0);
  });

  it('should handle negative numbers', () => {
    const compareFn = defaultComparator<{ value: number }, 'value'>('value');
    const a = { value: -10 };
    const b = { value: 5 };

    expect(compareFn(a, b)).toBeLessThan(0);
    expect(compareFn(b, a)).toBeGreaterThan(0);
  });

  it('should compare dates by value', () => {
    const compareFn = defaultComparator<{ date: Date }, 'date'>('date');
    const a = { date: new Date('2023-01-01') };
    const b = { date: new Date('2024-01-01') };

    expect(compareFn(a, b)).toBeLessThan(0);
    expect(compareFn(b, a)).toBeGreaterThan(0);
  });

  it('should be case-sensitive for strings', () => {
    const compareFn = defaultComparator<{ name: string }, 'name'>('name');
    const a = { name: 'alice' };
    const b = { name: 'Alice' };

    expect(compareFn(a, b)).not.toBe(0);
  });

  it('should handle objects with multiple properties', () => {
    const compareFn = defaultComparator<{ name: string; age: number }, 'name'>(
      'name',
    );
    const a = { name: 'Alice', age: 25 };
    const b = { name: 'Bob', age: 30 };

    expect(compareFn(a, b)).toBeLessThan(0);
  });

  it('should use localeCompare for strings', () => {
    const compareFn = defaultComparator<{ text: string }, 'text'>('text');
    const a = { text: 'café' };
    const b = { text: 'cafe' };

    const result = compareFn(a, b);
    expect(result).not.toBe(0);
  });

  it('should sort empty or missing values at the end for A-Z order', () => {
    const compareFn = defaultComparator<{ name: string }, 'name'>('name');
    const a = { name: '' };
    const b = { name: 'Alice' };

    expect(compareFn(a, b)).toBeGreaterThan(0);
    expect(compareFn(b, a)).toBeLessThan(0);
  });

  it('should sort array with undefined and empty string at end in A-Z order', () => {
    const compareFn = defaultComparator<{ name: string | undefined }, 'name'>(
      'name',
    );
    const items = [
      { name: 'Charlie' },
      { name: undefined },
      { name: 'Alice' },
      { name: '' },
      { name: 'Bob' },
    ];

    const sorted = [...items].sort(compareFn);

    expect(sorted[0].name).toBe('Alice');
    expect(sorted[1].name).toBe('Bob');
    expect(sorted[2].name).toBe('Charlie');
    expect(sorted[3].name === '' || sorted[3].name === undefined).toBe(true);
    expect(sorted[4].name === '' || sorted[4].name === undefined).toBe(true);
  });

  it('should handle zero values', () => {
    const compareFn = defaultComparator<{ value: number }, 'value'>('value');
    const a = { value: 0 };
    const b = { value: 1 };

    expect(compareFn(a, b)).toBeLessThan(0);
    expect(compareFn(b, a)).toBeGreaterThan(0);
  });

  it('should work with boolean values', () => {
    const compareFn = defaultComparator<{ active: boolean }, 'active'>(
      'active',
    );
    const a = { active: false };
    const b = { active: true };

    expect(compareFn(a, b)).toBeLessThan(0);
    expect(compareFn(b, a)).toBeGreaterThan(0);
  });

  it('should correctly sort an array of objects', () => {
    const compareFn = defaultComparator<{ name: string }, 'name'>('name');
    const items = [
      { name: 'Charlie' },
      { name: 'Alice' },
      { name: 'Bob' },
      { name: 'Dave' },
    ];

    const sorted = [...items].sort(compareFn);

    expect(sorted[0].name).toBe('Alice');
    expect(sorted[1].name).toBe('Bob');
    expect(sorted[2].name).toBe('Charlie');
    expect(sorted[3].name).toBe('Dave');
  });

  it('should correctly sort an array of numbers', () => {
    const compareFn = defaultComparator<{ value: number }, 'value'>('value');
    const items = [{ value: 5 }, { value: 1 }, { value: 10 }, { value: 3 }];

    const sorted = [...items].sort(compareFn);

    expect(sorted[0].value).toBe(1);
    expect(sorted[1].value).toBe(3);
    expect(sorted[2].value).toBe(5);
    expect(sorted[3].value).toBe(10);
  });
});
