// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export enum WorkloadStatus {
  // Native K8s statuses (AIWB + AIRM)
  PENDING = 'Pending',
  RUNNING = 'Running',
  STARTING = 'Starting',
  COMPLETE = 'Complete',
  DEGRADED = 'Degraded',
  FAILED = 'Failed',
  DELETING = 'Deleting',
  DELETED = 'Deleted',
  UNKNOWN = 'Unknown',
  ADDED = 'Added',
  DOWNLOADING = 'Downloading',
  DELETE_FAILED = 'DeleteFailed',
  TERMINATED = 'Terminated',
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
