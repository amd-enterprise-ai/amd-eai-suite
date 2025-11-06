// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export function compareUsersByFullName<
  T extends { firstName: string; lastName: string },
>(a: T, b: T): number {
  const firstNameComparison = a.firstName.localeCompare(b.firstName);
  if (firstNameComparison !== 0) return firstNameComparison;
  return a.lastName.localeCompare(b.lastName);
}
