// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import {
  ProjectStorageStatus,
  StorageScope,
  StorageStatus,
  StorageType,
} from '@/types/enums/storages';
import {
  ProjectStorage,
  ProjectStorageWithParentStorage,
  Storage,
} from '@/types/storages';

export const generateMockStorages = (n: number): Storage[] => {
  return Array.from({ length: n }, (_, index) => ({
    id: `storage-${index}`,
    name: `Storage ${index}`,
    displayName: `Storage ${index}`,
    type: StorageType.S3,
    status: StorageStatus.SYNCED,
    statusReason: null,
    scope: StorageScope.ORGANIZATION,
    createdAt: new Date().toISOString(),
    createdBy: `user-${index}`,
    updatedAt: new Date().toISOString(),
    updatedBy: `user-${index}`,
    projectStorages: generateMockProjectStorages(2),
    secretId: `secret-${index}`,
  }));
};

export const generateMockProjectStorages = (n: number): ProjectStorage[] => {
  return Array.from({ length: n }, (_, index) => ({
    id: `project-storage-${index}`,
    name: `Project Storage ${index}`,
    displayName: `Project Storage ${index}`,
    type: StorageType.S3,
    status: ProjectStorageStatus.SYNCED,
    statusReason: null,
    scope: StorageScope.PROJECT,
    createdAt: new Date().toISOString(),
    createdBy: `user-${index}`,
    updatedAt: new Date().toISOString(),
    updatedBy: `user-${index}`,
    projectId: `project-${index}`,
    projectName: `Project ${index}`,
    projectStorages: [],
  }));
};

export const generateMockProjectStoragesWithParentStorage = (
  n: number,
  projectId?: string,
): ProjectStorageWithParentStorage[] => {
  return Array.from({ length: n }, (_, i) => ({
    id: `project-storage-${i + 1}`,
    name: `My project storage ${i + 1}`,
    projectId: projectId ?? `project-${i + 1}`,
    projectName: `Project Name ${i + 1}`,
    displayName: `My Project Display Name ${i + 1}`,
    scope: StorageScope.PROJECT,
    status: ProjectStorageStatus.PENDING,
    statusReason: '',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    createdBy: `user-${i + 1}`,
    updatedBy: `user-${i + 1}`,
    storage: generateMockStorages(1)[0],
  }));
};
