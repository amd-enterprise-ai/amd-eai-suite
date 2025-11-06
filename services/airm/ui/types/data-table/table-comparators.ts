// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export type Comparator<T> = (a: T, b: T) => number;

export type CustomComparatorConfig<T, K extends string | number | symbol> = {
  [key in K]?: Comparator<T>;
};
