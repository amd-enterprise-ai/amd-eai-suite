// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  IconAlertTriangle,
  IconCircleCaretRight,
  IconCircleCheck,
  IconCircleX,
  IconQuestionMark,
} from '@tabler/icons-react';

import { StatusBadgeVariant } from '@/types/data-table/status-variant';
import { WorkloadStatus } from '@/types/enums/workloads';

export const getWorkloadStatusVariants = (
  t: (key: string) => string,
): Record<WorkloadStatus, StatusBadgeVariant> => ({
  [WorkloadStatus.ADDED]: {
    label: t(`status.${WorkloadStatus.ADDED}`),
    icon: IconCircleCheck,
    color: 'success',
  },
  [WorkloadStatus.COMPLETE]: {
    label: t(`status.${WorkloadStatus.COMPLETE}`),
    icon: IconCircleCheck,
    color: 'success',
  },
  [WorkloadStatus.RUNNING]: {
    label: t(`status.${WorkloadStatus.RUNNING}`),
    icon: IconCircleCaretRight,
    color: 'success',
  },
  [WorkloadStatus.DELETING]: {
    label: t(`status.${WorkloadStatus.DELETING}`),
    icon: 'spinner',
    color: 'warning',
  },
  [WorkloadStatus.PENDING]: {
    label: t(`status.${WorkloadStatus.PENDING}`),
    color: 'primary',
    icon: 'spinner',
  },
  [WorkloadStatus.FAILED]: {
    label: t(`status.${WorkloadStatus.FAILED}`),
    icon: IconAlertTriangle,
    color: 'danger',
  },
  [WorkloadStatus.DELETE_FAILED]: {
    label: t(`status.${WorkloadStatus.DELETE_FAILED}`),
    icon: IconAlertTriangle,
    color: 'danger',
  },
  [WorkloadStatus.DELETED]: {
    label: t(`status.${WorkloadStatus.DELETED}`),
    icon: IconCircleX,
    color: 'default',
    textColor: 'default',
  },
  [WorkloadStatus.TERMINATED]: {
    label: t(`status.${WorkloadStatus.TERMINATED}`),
    icon: IconCircleX,
    color: 'danger',
  },
  [WorkloadStatus.DOWNLOADING]: {
    label: t(`status.${WorkloadStatus.DOWNLOADING}`),
    icon: 'spinner',
    color: 'primary',
  },
  [WorkloadStatus.UNKNOWN]: {
    label: t(`status.${WorkloadStatus.UNKNOWN}`),
    icon: IconQuestionMark,
    color: 'danger',
    textColor: 'danger',
  },
});

export default getWorkloadStatusVariants;
