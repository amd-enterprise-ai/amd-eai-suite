// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

/**
 * Represents a single filter item in the dropdown
 */
export interface FilterItem {
  key: string;
  label: string;
  description?: string;
  showDivider?: boolean;
}

export interface FilterStateConfig {
  selectedKeys?: string[];
  defaultSelectedKeys?: string[];
  items?: FilterItem[];
  onSelectionChange?: (keys: Set<string>) => void;
}

export interface FilterStateResult {
  hasUserInteracted: boolean;
  currentSelectedSet: Set<string>;
  handleSelectionChange: (keys: Set<string> | string[]) => void;
  handleReset: () => void;
}
