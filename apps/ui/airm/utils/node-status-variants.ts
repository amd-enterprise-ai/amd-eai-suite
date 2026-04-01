// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { IconAlertTriangle, IconCircleX } from '@tabler/icons-react';

import { Intent } from '@amdenterpriseai/types';
import { StatusBadgeVariant } from '@amdenterpriseai/types';

import { NodeStatus } from '@/utils/node-status';

/** Variants: Available (green circle), Unhealthy (triangle !), Not available (grey circle x), with label text. */
export const getNodeStatusVariants = (
  t: (key: string) => string,
): Record<NodeStatus, StatusBadgeVariant> => ({
  [NodeStatus.AVAILABLE]: {
    label: t('nodes.detail.status.available'),
    intent: Intent.SUCCESS,
  },
  [NodeStatus.UNHEALTHY]: {
    label: t('nodes.detail.status.unhealthy'),
    intent: Intent.DANGER,
    icon: IconAlertTriangle,
  },
  [NodeStatus.NOT_AVAILABLE]: {
    label: t('nodes.detail.status.notAvailable'),
    color: 'default',
    icon: IconCircleX,
  },
});
