// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { isNil } from 'lodash';

export const defaultComparator =
  <T, K extends string>(fieldKey: K) =>
  (a: T, b: T): number => {
    const aValue = (a as Record<string, any>)[fieldKey];
    const bValue = (b as Record<string, any>)[fieldKey];
    if (isNil(aValue) && isNil(bValue)) return 0;
    if (isNil(aValue)) return 1;
    if (isNil(bValue)) return -1;

    if (typeof aValue === 'string' && typeof bValue === 'string') {
      return aValue.localeCompare(bValue);
    }
    return aValue > bValue ? 1 : aValue < bValue ? -1 : 0;
  };

export const dateComparator = (
  a: string | undefined,
  b: string | undefined,
): number => {
  if (!a && !b) return 0;
  if (!a) return -1;
  if (!b) return 1;
  return a.localeCompare(b);
};

export default defaultComparator;
