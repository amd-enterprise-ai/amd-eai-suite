// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { IconAlertTriangle } from '@tabler/icons-react';

import { StatusBadgeVariant } from '@/types/data-table/status-variant';

import { Intent } from '@/components/shared/Status/Status';
import { StorageStatus } from '@/types/enums/storages';

export const getStorageStatusVariants = (
  t: (key: string) => string,
): Record<StorageStatus, StatusBadgeVariant> => ({
  [StorageStatus.PENDING]: {
    label: t(`storageStatus.${StorageStatus.PENDING}`),
    intent: Intent.PENDING,
    color: 'warning',
  },
  [StorageStatus.PARTIALLY_SYNCED]: {
    label: t(`storageStatus.${StorageStatus.PARTIALLY_SYNCED}`),
    intent: Intent.PENDING,
    color: 'warning',
  },
  [StorageStatus.SYNCED]: {
    label: t(`storageStatus.${StorageStatus.SYNCED}`),
    intent: Intent.SUCCESS,
  },
  [StorageStatus.SYNCED_ERROR]: {
    label: t(`storageStatus.${StorageStatus.SYNCED_ERROR}`),
    intent: Intent.DANGER,
  },
  [StorageStatus.FAILED]: {
    label: t(`storageStatus.${StorageStatus.FAILED}`),
    intent: Intent.DANGER,
  },
  [StorageStatus.DELETING]: {
    label: t(`storageStatus.${StorageStatus.DELETING}`),
    intent: Intent.PENDING,
    color: 'warning',
  },
  [StorageStatus.DELETED]: {
    label: t(`storageStatus.${StorageStatus.DELETED}`),
    intent: Intent.DANGER,
  },
  [StorageStatus.DELETE_FAILED]: {
    label: t(`storageStatus.${StorageStatus.DELETE_FAILED}`),
    intent: Intent.DANGER,
    icon: IconAlertTriangle,
  },
  [StorageStatus.UNASSIGNED]: {
    label: t(`storageStatus.${StorageStatus.UNASSIGNED}`),
    color: 'default',
  },
});

export default getStorageStatusVariants;
