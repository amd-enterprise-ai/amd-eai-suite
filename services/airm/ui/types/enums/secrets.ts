// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export enum SecretScope {
  USER = 'User',
  ORGANIZATION = 'Organization',
  PROJECT = 'Project',
}

export enum SecretStatus {
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

export enum SecretType {
  EXTERNAL_SECRET = 'ExternalSecret',
  KUBERNETES_SECRET = 'KubernetesSecret',
}

export enum SecretUseCase {
  HUGGING_FACE = 'HuggingFace',
  S3 = 'S3',
  DB = 'Database',
  GENERIC = 'Generic',
}

export enum ProjectSecretStatus {
  PENDING = 'Pending',
  SYNCED = 'Synced',
  FAILED = 'Failed',
  SYNCED_ERROR = 'SyncedError',
  DELETING = 'Deleting',
  DELETED = 'Deleted',
  DELETE_FAILED = 'DeleteFailed',
}
