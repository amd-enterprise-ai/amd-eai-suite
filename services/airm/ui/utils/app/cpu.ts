// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

const MillicoreMultiplier = 1000;

export const millicoresToCpus = (millicores: number) => {
  return parseFloat((millicores / MillicoreMultiplier).toFixed(3));
};
