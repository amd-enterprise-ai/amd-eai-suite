// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export enum WorkloadStatus {
  // Native K8s statuses (AIWB + AIRM)
  PENDING = 'Pending',
  RUNNING = 'Running',
  COMPLETE = 'Complete',
  FAILED = 'Failed',
  DEGRADED = 'Degraded',
  DELETING = 'Deleting',
  DELETED = 'Deleted',
  UNKNOWN = 'Unknown',
  // AIRM only
  ADDED = 'Added',
  DOWNLOADING = 'Downloading',
  DELETE_FAILED = 'DeleteFailed',
  TERMINATED = 'Terminated',
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

export enum ResourceType {
  DEPLOYMENT = 'Deployment',
  JOB = 'Job',
  AIM_SERVICE = 'AIMService',
}
