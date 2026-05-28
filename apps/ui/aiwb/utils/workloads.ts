// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  IconAlertTriangle,
  IconCircleCaretRight,
  IconQuestionMark,
} from '@tabler/icons-react';

import {
  AvailableChartColorsKeys,
  Intent,
  StatusBadgeVariant,
} from '@amdenterpriseai/types';
import { WorkloadStatus } from '@/types/enums/workloads';

export const WORKLOAD_STATUS_COLOR_MAP: Record<
  WorkloadStatus,
  AvailableChartColorsKeys
> = {
  [WorkloadStatus.FAILED]: 'red',
  [WorkloadStatus.PENDING]: 'gray',
  [WorkloadStatus.RUNNING]: 'blue',
  [WorkloadStatus.COMPLETE]: 'green',
  [WorkloadStatus.DELETE_FAILED]: 'amber',
  [WorkloadStatus.TERMINATED]: 'gray',
  [WorkloadStatus.UNKNOWN]: 'darkgray',
  [WorkloadStatus.DELETED]: 'emerald',
  [WorkloadStatus.DELETING]: 'fuchsia',
  [WorkloadStatus.ADDED]: 'emerald',
  [WorkloadStatus.DEGRADED]: 'amber',
  [WorkloadStatus.STARTING]: 'blue',
  [WorkloadStatus.DOWNLOADING]: 'blue',
};

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
  [WorkloadStatus.STARTING]: {
    label: t(`status.${WorkloadStatus.STARTING}`),
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
