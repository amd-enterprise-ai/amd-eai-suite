// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export const defaultComparator =
  <T, K extends string>(fieldKey: K) =>
  (a: T, b: T): number => {
    const aValue = (a as Record<string, any>)[fieldKey];
    const bValue = (b as Record<string, any>)[fieldKey];
    if (typeof aValue === 'string' && typeof bValue === 'string') {
      return aValue.localeCompare(bValue);
    }
    return aValue > bValue ? 1 : aValue < bValue ? -1 : 0;
  };

export default defaultComparator;
