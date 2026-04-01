// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

/**
 * Display state for node status. Used only for UI (i18n keys, icons).
 * Backend may return different strings; map them with getNodeDisplayStatus().
 */
export enum NodeStatus {
  AVAILABLE = 'available',
  UNHEALTHY = 'unhealthy',
  NOT_AVAILABLE = 'notAvailable',
}

/** Maps backend node status string to display state. Display text comes from i18n, not from the backend. */
export function getNodeDisplayStatus(backendStatus: string): NodeStatus {
  const s = backendStatus?.trim() ?? '';
  if (s === 'Ready' || s === 'Healthy' || s === 'Available')
    return NodeStatus.AVAILABLE;
  if (s === 'Unhealthy') return NodeStatus.UNHEALTHY;
  if (s === 'Not available') return NodeStatus.NOT_AVAILABLE;
  return NodeStatus.NOT_AVAILABLE;
}
