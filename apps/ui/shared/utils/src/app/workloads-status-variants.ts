// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  IconAlertTriangle,
  IconCircleCaretRight,
  IconQuestionMark,
} from '@tabler/icons-react';

import { StatusBadgeVariant } from '@amdenterpriseai/types';
import { WorkloadStatus } from '@amdenterpriseai/types';
import { Intent } from '@amdenterpriseai/types';

export const getWorkloadStatusVariants = (
  t: (key: string) => string,
): Record<WorkloadStatus, StatusBadgeVariant> => ({
  [WorkloadStatus.ADDED]: {
    label: t(`status.${WorkloadStatus.ADDED}`),
    intent: Intent.SUCCESS,
  },
  [WorkloadStatus.COMPLETE]: {
    label: t(`status.${WorkloadStatus.COMPLETE}`),
    intent: Intent.SUCCESS,
  },
  [WorkloadStatus.DEGRADED]: {
    label: t(`status.${WorkloadStatus.DEGRADED}`),
    intent: Intent.WARNING,
  },
  [WorkloadStatus.RUNNING]: {
    label: t(`status.${WorkloadStatus.RUNNING}`),
    icon: IconCircleCaretRight,
    color: 'primary',
  },
  [WorkloadStatus.DELETING]: {
    label: t(`status.${WorkloadStatus.DELETING}`),
    intent: Intent.PENDING,
    color: 'warning',
  },
  [WorkloadStatus.PENDING]: {
    label: t(`status.${WorkloadStatus.PENDING}`),
    intent: Intent.PENDING,
  },
  [WorkloadStatus.FAILED]: {
    label: t(`status.${WorkloadStatus.FAILED}`),
    intent: Intent.DANGER,
  },
  [WorkloadStatus.DELETE_FAILED]: {
    label: t(`status.${WorkloadStatus.DELETE_FAILED}`),
    icon: IconAlertTriangle,
    intent: Intent.DANGER,
  },
  [WorkloadStatus.DELETED]: {
    label: t(`status.${WorkloadStatus.DELETED}`),
    intent: Intent.DANGER,
  },
  [WorkloadStatus.TERMINATED]: {
    label: t(`status.${WorkloadStatus.TERMINATED}`),
    intent: Intent.DANGER,
  },
  [WorkloadStatus.DOWNLOADING]: {
    label: t(`status.${WorkloadStatus.DOWNLOADING}`),
    intent: Intent.PENDING,
  },
  [WorkloadStatus.UNKNOWN]: {
    label: t(`status.${WorkloadStatus.UNKNOWN}`),
    icon: IconQuestionMark,
    color: 'danger',
  },
});

export default getWorkloadStatusVariants;
