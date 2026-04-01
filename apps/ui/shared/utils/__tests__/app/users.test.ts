// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { describe, it, expect } from 'vitest';
import { compareUsersByFullName } from '@amdenterpriseai/utils/app';

describe('compareUsersByFullName', () => {
  it('should sort by first name when they differ', () => {
    const alice = { firstName: 'Alice', lastName: 'Smith' };
    const bob = { firstName: 'Bob', lastName: 'Smith' };

    expect(compareUsersByFullName(alice, bob)).toBeLessThan(0);
    expect(compareUsersByFullName(bob, alice)).toBeGreaterThan(0);
  });

  it('should sort by last name when first names are equal', () => {
    const alice = { firstName: 'John', lastName: 'Adams' };
    const bob = { firstName: 'John', lastName: 'Brown' };

    expect(compareUsersByFullName(alice, bob)).toBeLessThan(0);
    expect(compareUsersByFullName(bob, alice)).toBeGreaterThan(0);
  });

  it('should return 0 for identical full names', () => {
    const user1 = { firstName: 'John', lastName: 'Smith' };
    const user2 = { firstName: 'John', lastName: 'Smith' };

    expect(compareUsersByFullName(user1, user2)).toBe(0);
  });

  it('should be case-sensitive', () => {
    const alice = { firstName: 'alice', lastName: 'Smith' };
    const alice2 = { firstName: 'Alice', lastName: 'Smith' };

    // localeCompare is case-sensitive and differs for same letters with different cases
    const result = compareUsersByFullName(alice, alice2);
    expect(result).not.toBe(0);
  });

  it('should handle empty first names', () => {
    const user1 = { firstName: '', lastName: 'Smith' };
    const user2 = { firstName: 'Alice', lastName: 'Smith' };

    expect(compareUsersByFullName(user1, user2)).toBeLessThan(0);
  });

  it('should handle empty last names', () => {
    const user1 = { firstName: 'Alice', lastName: '' };
    const user2 = { firstName: 'Alice', lastName: 'Smith' };

    expect(compareUsersByFullName(user1, user2)).toBeLessThan(0);
  });

  it('should handle special characters in names', () => {
    const user1 = { firstName: "O'Brien", lastName: 'Smith' };
    const user2 = { firstName: 'OBrien', lastName: 'Smith' };

    const result = compareUsersByFullName(user1, user2);
    expect(result).not.toBe(0);
  });

  it('should work with objects having additional properties', () => {
    const user1 = { firstName: 'Alice', lastName: 'Smith', age: 30, id: '1' };
    const user2 = { firstName: 'Bob', lastName: 'Jones', age: 25, id: '2' };

    expect(compareUsersByFullName(user1, user2)).toBeLessThan(0);
  });

  it('should correctly order multiple users', () => {
    const users = [
      { firstName: 'Charlie', lastName: 'Brown' },
      { firstName: 'Alice', lastName: 'Smith' },
      { firstName: 'Bob', lastName: 'Jones' },
      { firstName: 'Alice', lastName: 'Adams' },
    ];

    const sorted = [...users].sort(compareUsersByFullName);

    expect(sorted[0].firstName).toBe('Alice');
    expect(sorted[0].lastName).toBe('Adams');
    expect(sorted[1].firstName).toBe('Alice');
    expect(sorted[1].lastName).toBe('Smith');
    expect(sorted[2].firstName).toBe('Bob');
    expect(sorted[3].firstName).toBe('Charlie');
  });
});
