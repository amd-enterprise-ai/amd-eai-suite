// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { describe, it, expect } from 'vitest';

import {
  doesProjectStorageDataNeedToBeRefreshed,
  doesStorageDataNeedToBeRefreshed,
} from '@/utils/storages';
import {
  ProjectStorageStatus,
  StorageScope,
  StorageStatus,
} from '@/types/enums/storages';
import { GPU_PREEMPTION_DISABLED } from '@/types/projects';
import type { ProjectStorage, Storage } from '@/types/storages';

describe('doesStorageDataNeedToBeRefreshed', () => {
  it('should return false if list is empty', () => {
    expect(doesStorageDataNeedToBeRefreshed([])).toBe(false);
  });

  it('should return true if a storage has PENDING status', () => {
    const storages: Storage[] = [
      {
        id: '1',
        name: 'storage-1',
        status: StorageStatus.PENDING,
        statusReason: null,
        type: 'S3',
        size: 1000,
        projectStorages: [],
        scope: StorageScope.ORGANIZATION,
        createdAt: '2025-10-01T00:00:00Z',
        createdBy: 'test@example.com',
        updatedAt: '2025-10-01T00:00:00Z',
        updatedBy: 'test@example.com',
        secretId: 'secret-1',
      } as Storage,
    ];
    expect(doesStorageDataNeedToBeRefreshed(storages)).toBe(true);
  });

  it('should return true if a storage has PARTIALLY_SYNCED status', () => {
    const storages: Storage[] = [
      {
        id: '1',
        name: 'storage-1',
        status: StorageStatus.PARTIALLY_SYNCED,
        statusReason: null,
        type: 'S3',
        projectStorages: [],
        scope: StorageScope.ORGANIZATION,
        createdAt: '2025-10-01T00:00:00Z',
        createdBy: 'test@example.com',
        updatedAt: '2025-10-01T00:00:00Z',
        updatedBy: 'test@example.com',
        secretId: 'secret-1',
      } as Storage,
    ];
    expect(doesStorageDataNeedToBeRefreshed(storages)).toBe(true);
  });

  it('should return true if a storage has DELETING status', () => {
    const storages: Storage[] = [
      {
        id: '1',
        name: 'storage-1',
        status: StorageStatus.DELETING,
        statusReason: null,
        type: 'S3',
        projectStorages: [],
        scope: StorageScope.ORGANIZATION,
        createdAt: '2025-10-01T00:00:00Z',
        createdBy: 'test@example.com',
        updatedAt: '2025-10-01T00:00:00Z',
        updatedBy: 'test@example.com',
        secretId: 'secret-1',
      } as Storage,
    ];
    expect(doesStorageDataNeedToBeRefreshed(storages)).toBe(true);
  });

  it('should return false if no storage has refresh-requiring status', () => {
    const storages: Storage[] = [
      {
        id: '1',
        name: 'storage-1',
        status: StorageStatus.SYNCED,
        statusReason: null,
        type: 'S3',
        projectStorages: [],
        scope: StorageScope.ORGANIZATION,
        createdAt: '2025-10-01T00:00:00Z',
        createdBy: 'test@example.com',
        updatedAt: '2025-10-01T00:00:00Z',
        updatedBy: 'test@example.com',
        secretId: 'secret-1',
      } as Storage,
    ];
    expect(doesStorageDataNeedToBeRefreshed(storages)).toBe(false);
  });

  it('should return true if at least one storage needs refresh', () => {
    const storages: Storage[] = [
      {
        id: '1',
        name: 'storage-1',
        status: StorageStatus.SYNCED,
        statusReason: null,
        type: 'S3',
        projectStorages: [],
        scope: StorageScope.ORGANIZATION,
        createdAt: '2025-10-01T00:00:00Z',
        createdBy: 'test@example.com',
        updatedAt: '2025-10-01T00:00:00Z',
        updatedBy: 'test@example.com',
        secretId: 'secret-1',
      } as Storage,
      {
        id: '2',
        name: 'storage-2',
        status: StorageStatus.PENDING,
        statusReason: null,
        type: 'S3',
        projectStorages: [],
        scope: StorageScope.ORGANIZATION,
        createdAt: '2025-10-01T00:00:00Z',
        createdBy: 'test@example.com',
        updatedAt: '2025-10-01T00:00:00Z',
        updatedBy: 'test@example.com',
        secretId: 'secret-1',
      } as Storage,
    ];
    expect(doesStorageDataNeedToBeRefreshed(storages)).toBe(true);
  });
});

describe('doesProjectStorageDataNeedToBeRefreshed', () => {
  it('should return false if list is empty', () => {
    expect(doesProjectStorageDataNeedToBeRefreshed([])).toBe(false);
  });

  it('should return true if a project storage has PENDING status', () => {
    const projectStorages: ProjectStorage[] = [
      {
        id: '1',
        name: 'project-storage-1',
        status: ProjectStorageStatus.PENDING,
        statusReason: null,
        project: {
          id: 'project-1',
          name: 'Project 1',
          description: 'Test project',
          status: 'Ready',
          statusReason: null,
          clusterId: 'cluster-1',
          gpuPreemption: GPU_PREEMPTION_DISABLED,
        },
        scope: StorageScope.ORGANIZATION,
        createdAt: '2025-10-01T00:00:00Z',
        createdBy: 'test@example.com',
        updatedAt: '2025-10-01T00:00:00Z',
        updatedBy: 'test@example.com',
        storage: {
          id: 'storage-1',
          name: 'Storage 1',
          status: StorageStatus.PENDING,
          statusReason: null,
          type: 'S3',
          scope: StorageScope.ORGANIZATION,
          createdAt: '2025-10-01T00:00:00Z',
          createdBy: 'test@example.com',
          updatedAt: '2025-10-01T00:00:00Z',
          updatedBy: 'test@example.com',
        },
      } as ProjectStorage,
    ];
    expect(doesProjectStorageDataNeedToBeRefreshed(projectStorages)).toBe(true);
  });

  it('should return true if a project storage has DELETING status', () => {
    const projectStorages: ProjectStorage[] = [
      {
        id: '1',
        name: 'project-storage-1',
        status: ProjectStorageStatus.DELETING,
        statusReason: null,
        project: {
          id: 'project-1',
          name: 'Project 1',
          description: 'Test project',
          status: 'Ready',
          statusReason: null,
          clusterId: 'cluster-1',
          gpuPreemption: GPU_PREEMPTION_DISABLED,
        },
        scope: StorageScope.ORGANIZATION,
        createdAt: '2025-10-01T00:00:00Z',
        createdBy: 'test@example.com',
        updatedAt: '2025-10-01T00:00:00Z',
        updatedBy: 'test@example.com',
        storage: {
          id: 'storage-1',
          name: 'Storage 1',
          status: StorageStatus.PENDING,
          statusReason: null,
          type: 'S3',
          scope: StorageScope.ORGANIZATION,
          createdAt: '2025-10-01T00:00:00Z',
          createdBy: 'test@example.com',
          updatedAt: '2025-10-01T00:00:00Z',
          updatedBy: 'test@example.com',
        },
      } as ProjectStorage,
    ];
    expect(doesProjectStorageDataNeedToBeRefreshed(projectStorages)).toBe(true);
  });

  it('should return false if no project storage has refresh-requiring status', () => {
    const projectStorages: ProjectStorage[] = [
      {
        id: '1',
        name: 'project-storage-1',
        status: ProjectStorageStatus.SYNCED,
        statusReason: null,
        project: {
          id: 'project-1',
          name: 'Project 1',
          description: 'Test project',
          status: 'Ready',
          statusReason: null,
          clusterId: 'cluster-1',
          gpuPreemption: GPU_PREEMPTION_DISABLED,
        },
        scope: StorageScope.ORGANIZATION,
        createdAt: '2025-10-01T00:00:00Z',
        createdBy: 'test@example.com',
        updatedAt: '2025-10-01T00:00:00Z',
        updatedBy: 'test@example.com',
        storage: {
          id: 'storage-1',
          name: 'Storage 1',
          status: StorageStatus.PENDING,
          statusReason: null,
          type: 'S3',
          scope: StorageScope.ORGANIZATION,
          createdAt: '2025-10-01T00:00:00Z',
          createdBy: 'test@example.com',
          updatedAt: '2025-10-01T00:00:00Z',
          updatedBy: 'test@example.com',
        },
      } as ProjectStorage,
    ];
    expect(doesProjectStorageDataNeedToBeRefreshed(projectStorages)).toBe(
      false,
    );
  });

  it('should return true if at least one project storage needs refresh', () => {
    const projectStorages: ProjectStorage[] = [
      {
        id: '1',
        name: 'project-storage-1',
        status: ProjectStorageStatus.SYNCED,
        statusReason: null,
        project: {
          id: 'project-1',
          name: 'Project 1',
          description: 'Test project',
          status: 'Ready',
          statusReason: null,
          clusterId: 'cluster-1',
          gpuPreemption: GPU_PREEMPTION_DISABLED,
        },
        scope: StorageScope.ORGANIZATION,
        createdAt: '2025-10-01T00:00:00Z',
        createdBy: 'test@example.com',
        updatedAt: '2025-10-01T00:00:00Z',
        updatedBy: 'test@example.com',
        storage: {
          id: 'storage-1',
          name: 'Storage 1',
          status: StorageStatus.PENDING,
          statusReason: null,
          type: 'S3',
          scope: StorageScope.ORGANIZATION,
          createdAt: '2025-10-01T00:00:00Z',
          createdBy: 'test@example.com',
          updatedAt: '2025-10-01T00:00:00Z',
          updatedBy: 'test@example.com',
        },
      } as ProjectStorage,
      {
        id: '2',
        name: 'project-storage-2',
        status: ProjectStorageStatus.PENDING,
        statusReason: null,
        project: {
          id: 'project-1',
          name: 'Project 1',
          description: 'Test project',
          status: 'Ready',
          statusReason: null,
          clusterId: 'cluster-1',
          gpuPreemption: GPU_PREEMPTION_DISABLED,
        },
        scope: StorageScope.ORGANIZATION,
        createdAt: '2025-10-01T00:00:00Z',
        createdBy: 'test@example.com',
        updatedAt: '2025-10-01T00:00:00Z',
        updatedBy: 'test@example.com',
        storage: {
          id: 'storage-1',
          name: 'Storage 1',
          status: StorageStatus.PENDING,
          statusReason: null,
          type: 'S3',
          scope: StorageScope.ORGANIZATION,
          createdAt: '2025-10-01T00:00:00Z',
          createdBy: 'test@example.com',
          updatedAt: '2025-10-01T00:00:00Z',
          updatedBy: 'test@example.com',
        },
      } as ProjectStorage,
    ];
    expect(doesProjectStorageDataNeedToBeRefreshed(projectStorages)).toBe(true);
  });
});
