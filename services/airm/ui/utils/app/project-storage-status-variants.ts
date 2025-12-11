// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { StatusBadgeVariant } from '@/types/data-table/status-variant';

import { ProjectStorageStatus } from '@/types/enums/storages';
import { Intent } from '@/components/shared/Status/Status';

export const getProjectStorageStatusVariants = (
  t: (key: string) => string,
): Record<ProjectStorageStatus, StatusBadgeVariant> => ({
  [ProjectStorageStatus.PENDING]: {
    label: t(`storageStatus.${ProjectStorageStatus.PENDING}`),
    color: 'warning',
    intent: Intent.PENDING,
  },
  [ProjectStorageStatus.SYNCED]: {
    label: t(`storageStatus.${ProjectStorageStatus.SYNCED}`),
    intent: Intent.SUCCESS,
  },
  [ProjectStorageStatus.SYNCED_ERROR]: {
    label: t(`storageStatus.${ProjectStorageStatus.SYNCED_ERROR}`),
    intent: Intent.DANGER,
  },
  [ProjectStorageStatus.FAILED]: {
    label: t(`storageStatus.${ProjectStorageStatus.FAILED}`),
    intent: Intent.DANGER,
  },
  [ProjectStorageStatus.DELETING]: {
    label: t(`storageStatus.${ProjectStorageStatus.DELETING}`),
    color: 'warning',
    intent: Intent.PENDING,
  },
  [ProjectStorageStatus.DELETED]: {
    label: t(`storageStatus.${ProjectStorageStatus.DELETED}`),
    intent: Intent.DANGER,
  },
  [ProjectStorageStatus.DELETE_FAILED]: {
    label: t(`storageStatus.${ProjectStorageStatus.DELETE_FAILED}`),
    intent: Intent.DANGER,
  },
});

export default getProjectStorageStatusVariants;
