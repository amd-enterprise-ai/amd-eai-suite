// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { AvailableChartColorsKeys } from '@/utils/app/tremor-charts/utils';

export type CategoryValue = {
  label: string;
  value: number;
  color?: AvailableChartColorsKeys;
};

export type CategoryData = {
  title: string;
  total: number;
  values: CategoryValue[];
};
