// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export enum ProjectFormFields {
  NAME = 'name',
  DESCRIPTION = 'description',
  CLUSTER_ID = 'clusterId',
}

/** Create-project drawer: workload GPU pre-emption (POST /v1/projects). */
export enum ProjectGpuPreemptionFormFields {
  ENABLED = 'gpuPreemptionEnabled',
  POLICY = 'gpuPreemptionPolicy',
  THRESHOLD = 'gpuPreemptionThreshold',
  GRACE_PERIOD = 'gpuPreemptionGracePeriod',
}
