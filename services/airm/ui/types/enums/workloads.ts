// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export enum WorkloadStatus {
  ADDED = 'Added',
  COMPLETE = 'Complete',
  DOWNLOADING = 'Downloading',
  FAILED = 'Failed',
  DELETING = 'Deleting',
  DELETE_FAILED = 'DeleteFailed',
  DELETED = 'Deleted',
  PENDING = 'Pending',
  RUNNING = 'Running',
  TERMINATED = 'Terminated',
  UNKNOWN = 'Unknown',
}

export enum WorkloadType {
  MODEL_DOWNLOAD = 'MODEL_DOWNLOAD',
  INFERENCE = 'INFERENCE',
  FINE_TUNING = 'FINE_TUNING',
  WORKSPACE = 'WORKSPACE',
  CUSTOM = 'CUSTOM',
}

export enum LogLevel {
  TRACE = 'trace',
  DEBUG = 'debug',
  INFO = 'info',
  UNKNOWN = 'unknown',
  WARNING = 'warning',
  ERROR = 'error',
  CRITICAL = 'critical',
}

export enum LogType {
  WORKLOAD = 'workload',
  EVENT = 'event',
}
