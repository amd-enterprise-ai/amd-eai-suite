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
