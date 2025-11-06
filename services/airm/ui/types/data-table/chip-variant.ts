// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Color } from '@/types/colors';

export type ChipDisplayVariant = {
  label: string;
  color?: Color;
  icon?: React.ComponentType<{ size?: string; className?: string }>;
};
