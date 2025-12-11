// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { IconProgressCheck } from '@tabler/icons-react';

import { StatusBadgeVariant } from '@/types/data-table/status-variant';

import { ProjectStatus } from '@/types/enums/projects';
import { Intent } from '@/components/shared/Status/Status';

export const getProjectStatusVariants = (
  t: (key: string) => string,
): Record<ProjectStatus, StatusBadgeVariant> => ({
  [ProjectStatus.READY]: {
    label: t(`status.${ProjectStatus.READY}`),
    intent: Intent.SUCCESS,
  },
  [ProjectStatus.PARTIALLY_READY]: {
    label: t(`status.${ProjectStatus.PARTIALLY_READY}`),
    icon: IconProgressCheck,
    color: 'primary',
  },
  [ProjectStatus.PENDING]: {
    label: t(`status.${ProjectStatus.PENDING}`),
    intent: Intent.PENDING,
  },
  [ProjectStatus.DELETING]: {
    label: t(`status.${ProjectStatus.DELETING}`),
    intent: Intent.PENDING,
  },
  [ProjectStatus.FAILED]: {
    label: t(`status.${ProjectStatus.FAILED}`),
    intent: Intent.DANGER,
  },
});

export default getProjectStatusVariants;
