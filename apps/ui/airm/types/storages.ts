// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import {
  ProjectStorageStatus,
  StorageScope,
  StorageStatus,
  StorageType,
} from './enums/storages';
import { ProjectBasicInfo } from './projects';

export type AddStorageButtonOptions = Partial<{
  [key in StorageType]: () => void;
}>;

export type S3StorageSpec = {
  bucketUrl: string;
  accessKeyName: string;
  secretKeyName: string;
};

export type CreateStorageRequest = {
  type: StorageType;
  name: string;
  scope: StorageScope;
  spec: S3StorageSpec;
  secretId: string;
  projectIds: string[];
};

export type AddS3StorageFormData = {
  name: string;
  secretId: string;
  projectIds: string[];
} & S3StorageSpec;

export type AssignStorageRequest = {
  projectIds: string[];
};

export type AssignStorageFormData = {
  projectIds: string[];
};

export type ProjectStorage = {
  id: string;
  project: ProjectBasicInfo;
  scope: StorageScope;
  status: ProjectStorageStatus;
  statusReason: string | null;
  createdAt: string;
  createdBy: string;
  updatedAt: string;
  updatedBy: string;
  storage: BaseStorage;
};

export type BaseStorage = {
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
  data: Storage[];
};

export type ProjectStoragesResponse = {
  data: ProjectStorageWithParentStorage[];
};
