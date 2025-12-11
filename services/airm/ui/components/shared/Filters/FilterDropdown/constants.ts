// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

/**
 * Constants used throughout the FilterDropdown component
 */

export const FILTER_CONSTANTS = {
  /** Debounce delay for external state synchronization (ms) */
  DEBOUNCE_DELAY: 300,

  /** Timeout for internal state sync operations (ms) */
  STATE_SYNC_TIMEOUT: 100,

  /** Delay before showing tooltips (ms) */
  TOOLTIP_DELAY: 500,

  /** Minimum dropdown width */
  MIN_DROPDOWN_WIDTH: 'min-w-64',
} as const;
