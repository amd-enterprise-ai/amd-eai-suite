// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export enum QuotaResource {
  GPU = 'gpuCount',
  CPU = 'cpuMilliCores',
  RAM = 'memoryBytes',
  DISK = 'ephemeralStorageBytes',
}

export enum QuotaStatus {
  PENDING = 'Pending',
  READY = 'Ready',
  DELETING = 'Deleting',
  FAILED = 'Failed',
}
