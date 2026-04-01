// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { IconCircleCaretRight } from '@tabler/icons-react';

import { StatusBadgeVariant } from '@amdenterpriseai/types';

import { Intent } from '@amdenterpriseai/types';
import { ClusterStatus } from '@amdenterpriseai/types';

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
