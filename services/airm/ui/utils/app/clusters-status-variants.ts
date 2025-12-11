// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { IconCircleCaretRight } from '@tabler/icons-react';

import { StatusBadgeVariant } from '@/types/data-table/status-variant';

import { Intent } from '@/components/shared/Status/Status';
import { ClusterStatus } from '@/types/enums/cluster-status';

export const getClusterStatusVariants = (
  t: (key: string) => string,
): Record<ClusterStatus, StatusBadgeVariant> => ({
  [ClusterStatus.UNHEALTHY]: {
    label: t(`status.${ClusterStatus.UNHEALTHY}`),
    intent: Intent.DANGER,
  },
  [ClusterStatus.HEALTHY]: {
    label: t(`status.${ClusterStatus.HEALTHY}`),
    intent: Intent.SUCCESS,
  },
  [ClusterStatus.VERIFYING]: {
    label: t(`status.${ClusterStatus.VERIFYING}`),
    icon: IconCircleCaretRight,
    color: 'primary',
  },
});

export default getClusterStatusVariants;
