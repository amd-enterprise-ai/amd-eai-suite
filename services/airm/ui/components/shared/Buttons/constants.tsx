// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { IconLoaderQuarter } from '@tabler/icons-react';

// Static variant configurations - computed once, reused everywhere
export const VARIANT_CONFIGS = {
  primary: { variant: 'solid' as const, color: 'primary' as const },
  tertiary: { variant: 'light' as const, color: 'default' as const },
  secondary: { variant: 'flat' as const, color: 'default' as const }, // default
} as const;

// Static spinner element - created once, reused
export const SPINNER_ELEMENT = <IconLoaderQuarter className="animate-spin" />;
