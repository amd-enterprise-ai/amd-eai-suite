// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { FilterItem } from '@/components/shared/Filters/FilterDropdown/FilterDropdown';

export interface FilterStateConfig {
  selectedKeys?: string[];
  defaultSelectedKeys?: string[];
  items?: FilterItem[];
  onSelectionChange?: (keys: Set<string>) => void;
}

export interface FilterStateResult {
  internalSelectedKeys: string[];
  hasUserInteracted: boolean;
  currentSelectedSet: Set<string>;
  handleSelectionChange: (keys: Set<string> | string[]) => void;
  handleReset: () => void;
  onUserInteraction: () => void;
}
