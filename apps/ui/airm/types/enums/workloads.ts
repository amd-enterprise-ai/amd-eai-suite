// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export enum WorkloadStatus {
  // Native K8s statuses (AIWB + AIRM)
  PENDING = 'Pending',
  RUNNING = 'Running',
  COMPLETE = 'Complete',
  FAILED = 'Failed',
  DELETING = 'Deleting',
  DELETE_FAILED = 'DeleteFailed',
  DELETED = 'Deleted',
  UNKNOWN = 'Unknown',
  TERMINATED = 'Terminated',
}
