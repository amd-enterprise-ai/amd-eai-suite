// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import {
  ProjectStorageStatus,
  StorageScope,
  StorageStatus,
  StorageType,
} from './enums/storages';
import { SnakeCaseKeys } from './misc';

export type AddStorageButtonOptions = Partial<{
  [key in StorageType]: () => void;
}>;

export type S3StorageSpec = {
  bucketUrl: string;
  accessKeyName: string;
  secretKeyName: string;
};

export type S3StorageSpecServer = SnakeCaseKeys<S3StorageSpec>;

export type CreateStorageRequest = {
  type: StorageType;
  name: string;
  scope: StorageScope;
  spec: S3StorageSpecServer;
  secret_id: string;
  project_ids: string[];
};

export type AddS3StorageFormData = {
  name: string;
  secretId: string;
  projectIds: string[];
} & S3StorageSpec;

export type AssignStorageRequest = {
  project_ids: string[];
};

export type AssignStorageFormData = {
  projectIds: string[];
};

export type ProjectStorage = {
  id: string;
  projectId: string;
  projectName: string;
  scope: StorageScope;
  status: ProjectStorageStatus;
  statusReason: string | null;
  createdAt: string;
  createdBy: string;
  updatedAt: string;
  updatedBy: string;
};

export type BaseStorage = {
  displayName: string;
  id: string;
  name: string;
  type: StorageType;
  status: StorageStatus;
  statusReason: string | null;
  scope: StorageScope;
  createdAt: string;
  createdBy: string;
  updatedAt: string;
  updatedBy: string;
};

export type Storage = BaseStorage & {
  projectStorages: ProjectStorage[];
  secretId: string;
};

export type ProjectStorageWithParentStorage = ProjectStorage & {
  storage: Storage;
};

export type StoragesResponse = {
  storages: Storage[];
};

export type ProjectStoragesResponse = {
  projectStorages: ProjectStorageWithParentStorage[];
};
