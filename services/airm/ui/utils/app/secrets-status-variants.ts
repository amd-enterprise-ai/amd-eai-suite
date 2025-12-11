// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { StatusBadgeVariant } from '@/types/data-table/status-variant';

import { SecretStatus } from '@/types/enums/secrets';
import { Intent } from '@/components/shared/Status/Status';

export const getSecretStatusVariants = (
  t: (key: string) => string,
): Record<SecretStatus, StatusBadgeVariant> => ({
  [SecretStatus.PENDING]: {
    label: t(`secretStatus.${SecretStatus.PENDING}`),
    color: 'warning',
    intent: Intent.PENDING,
  },
  [SecretStatus.PARTIALLY_SYNCED]: {
    label: t(`secretStatus.${SecretStatus.PARTIALLY_SYNCED}`),
    color: 'warning',
    intent: Intent.PENDING,
  },
  [SecretStatus.SYNCED]: {
    label: t(`secretStatus.${SecretStatus.SYNCED}`),
    intent: Intent.SUCCESS,
  },
  [SecretStatus.SYNCED_ERROR]: {
    label: t(`secretStatus.${SecretStatus.SYNCED_ERROR}`),
    intent: Intent.DANGER,
  },
  [SecretStatus.FAILED]: {
    label: t(`secretStatus.${SecretStatus.FAILED}`),
    intent: Intent.DANGER,
  },
  [SecretStatus.DELETING]: {
    label: t(`secretStatus.${SecretStatus.DELETING}`),
    color: 'warning',
    intent: Intent.PENDING,
  },
  [SecretStatus.DELETED]: {
    label: t(`secretStatus.${SecretStatus.DELETED}`),
    intent: Intent.DANGER,
  },
  [SecretStatus.DELETE_FAILED]: {
    label: t(`secretStatus.${SecretStatus.DELETE_FAILED}`),
    intent: Intent.DANGER,
  },
  [SecretStatus.UNASSIGNED]: {
    label: t(`secretStatus.${SecretStatus.UNASSIGNED}`),
    color: 'default',
  },
});

export default getSecretStatusVariants;
