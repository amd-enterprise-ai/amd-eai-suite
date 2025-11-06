// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ProjectStorageStatus, StorageStatus } from '@/types/enums/storages';
import { ProjectStorage, Storage } from '@/types/storages';

export const doesStorageDataNeedToBeRefreshed = (secrets: Storage[]) => {
  return secrets.some(
    (c) =>
      c.status == StorageStatus.PENDING ||
      c.status == StorageStatus.PARTIALLY_SYNCED ||
      c.status == StorageStatus.DELETING,
  );
};

export const doesProjectStorageDataNeedToBeRefreshed = (
  secrets: ProjectStorage[],
) => {
  return secrets.some(
    (c) =>
      c.status == ProjectStorageStatus.PENDING ||
      c.status == ProjectStorageStatus.DELETING,
  );
};
