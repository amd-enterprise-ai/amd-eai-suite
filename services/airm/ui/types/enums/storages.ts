// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export enum StorageType {
  S3 = 'S3',
}

export enum StorageScope {
  ORGANIZATION = 'Organization',
  PROJECT = 'Project',
}

export enum StorageStatus {
  UNASSIGNED = 'Unassigned',
  PENDING = 'Pending',
  SYNCED = 'Synced',
  PARTIALLY_SYNCED = 'PartiallySynced',
  FAILED = 'Failed',
  SYNCED_ERROR = 'SyncedError',
  DELETING = 'Deleting',
  DELETED = 'Deleted',
  DELETE_FAILED = 'DeleteFailed',
}

export enum ProjectStorageStatus {
  PENDING = 'Pending',
  SYNCED = 'Synced',
  FAILED = 'Failed',
  SYNCED_ERROR = 'SyncedError',
  DELETING = 'Deleting',
  DELETED = 'Deleted',
  DELETE_FAILED = 'DeleteFailed',
}

export enum StoragesTableField {
  NAME = 'name',
  TYPE = 'type',
  STATUS = 'status',
  SCOPE = 'scope',
  ASSIGNED_TO = 'assignedTo',
  CREATED_AT = 'createdAt',
  CREATED_BY = 'createdBy',
  ACTIONS = 'actions',
}
