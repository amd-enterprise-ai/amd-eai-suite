// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export type ClusterResources = {
  availableResources: {
    gpuCount: number;
    cpuMilliCores: number;
    memoryBytes: number;
    ephemeralStorageBytes: number;
  };
  totalNodeCount: number;
};

export type AimImageFamily = {
  familyId: string;
  displayName: string;
  repository: string | null;
  tags: string[];
};

export type ClusterAccelerator = {
  deviceId: string;
  productName: string;
  allocatableCount: number;
};

export type ListResponse<T> = {
  data: T[];
};
