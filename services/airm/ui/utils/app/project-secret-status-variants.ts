// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { StatusBadgeVariant } from '@/types/data-table/status-variant';

import { ProjectSecretStatus } from '@/types/enums/secrets';
import { Intent } from '@/components/shared/Status/Status';

export const getProjectSecretStatusVariants = (
  t: (key: string) => string,
): Record<ProjectSecretStatus, StatusBadgeVariant> => ({
  [ProjectSecretStatus.PENDING]: {
    label: t(`secretStatus.${ProjectSecretStatus.PENDING}`),
    color: 'warning',
    intent: Intent.PENDING,
  },
  [ProjectSecretStatus.SYNCED]: {
    label: t(`secretStatus.${ProjectSecretStatus.SYNCED}`),
    intent: Intent.SUCCESS,
  },
  [ProjectSecretStatus.SYNCED_ERROR]: {
    label: t(`secretStatus.${ProjectSecretStatus.SYNCED_ERROR}`),
    intent: Intent.DANGER,
  },
  [ProjectSecretStatus.FAILED]: {
    label: t(`secretStatus.${ProjectSecretStatus.FAILED}`),
    intent: Intent.DANGER,
  },
  [ProjectSecretStatus.DELETING]: {
    label: t(`secretStatus.${ProjectSecretStatus.DELETING}`),
    color: 'warning',
    intent: Intent.PENDING,
  },
  [ProjectSecretStatus.DELETED]: {
    label: t(`secretStatus.${ProjectSecretStatus.DELETED}`),
    intent: Intent.DANGER,
  },
  [ProjectSecretStatus.DELETE_FAILED]: {
    label: t(`secretStatus.${ProjectSecretStatus.DELETE_FAILED}`),
    intent: Intent.DANGER,
  },
});

export default getProjectSecretStatusVariants;
