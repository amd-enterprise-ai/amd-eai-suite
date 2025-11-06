// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Color } from '@/types/colors';

export type StatusBadgeVariant = {
  label: string;
  color?: Color;
  textColor?: Color;
  icon: React.ComponentType<{ size?: string; className?: string }> | 'spinner';
};
