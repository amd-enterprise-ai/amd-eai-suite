// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export enum ClusterTableField {
  NAME = 'name',
  STATUS = 'status',
  NODES = 'nodes',
  GPU_ALLOCATION = 'gpuAllocation',
  CPU_ALLOCATION = 'cpuAllocation',
  MEMORY_ALLOCATION = 'memoryAllocation',
}

export enum PendingClusterTableField {
  REQUESTED_AT = 'requestedAt',
  REQUESTED_EXPIRY = 'requestExpiry',
  STATUS = 'status',
  ACTIONS = 'actions',
}
