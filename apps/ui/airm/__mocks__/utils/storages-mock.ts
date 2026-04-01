// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import {
  ProjectStorageStatus,
  StorageScope,
  StorageStatus,
  StorageType,
} from '@amdenterpriseai/types';
import {
  ProjectStorage,
  ProjectStorageWithParentStorage,
  Storage,
} from '@amdenterpriseai/types';
import { ProjectStatus } from '@amdenterpriseai/types';

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
    project: {
      id: `project-${index}`,
      name: `project-name-${index}`,
      description: `Project Description ${index}`,
      status: ProjectStatus.READY,
      statusReason: null,
      clusterId: `cluster-${index}`,
    },
    scope: StorageScope.ORGANIZATION,
    status: ProjectStorageStatus.SYNCED,
    statusReason: null,
    createdAt: new Date().toISOString(),
    createdBy: `user-${index}`,
    updatedAt: new Date().toISOString(),
    updatedBy: `user-${index}`,
    storage: {
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
      projectStorages: [],
      secretId: `secret-${index}`,
    },
  }));
};

export const generateMockProjectStoragesWithParentStorage = (
  n: number,
  projectId?: string,
): ProjectStorageWithParentStorage[] => {
  return Array.from({ length: n }, (_, i) => ({
    id: `project-storage-${i + 1}`,
    project: {
      id: projectId ?? `project-${i + 1}`,
      name: `project-name-${i + 1}`,
      description: `Project Description ${i + 1}`,
      status: ProjectStatus.READY,
      statusReason: null,
      clusterId: `cluster-${i + 1}`,
    },
    scope: StorageScope.ORGANIZATION,
    status: ProjectStorageStatus.PENDING,
    statusReason: '',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    createdBy: `user-${i + 1}`,
    updatedBy: `user-${i + 1}`,
    storage: generateMockStorages(1)[0],
  }));
};
