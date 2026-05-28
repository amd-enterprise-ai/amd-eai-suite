// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  AvailableChartColorsKeys,
  Intent,
  StatusBadgeVariant,
} from '@amdenterpriseai/types';
import { WorkloadType } from '@amdenterpriseai/types';
import { WorkloadFilterItem } from '@/types/workloads';

import { WorkloadStatus } from '@/types/enums/workloads';
import {
  IconAlertTriangle,
  IconCircleCaretRight,
  IconQuestionMark,
} from '@tabler/icons-react';

export const getWorkloadTypeFilterItems = (
  t: (key: string) => string,
): WorkloadFilterItem[] => [
  {
    key: WorkloadType.MODEL_DOWNLOAD,
    label: t(`type.${WorkloadType.MODEL_DOWNLOAD}`),
  },
  {
    key: WorkloadType.INFERENCE,
    label: t(`type.${WorkloadType.INFERENCE}`),
  },
  {
    key: WorkloadType.FINE_TUNING,
    label: t(`type.${WorkloadType.FINE_TUNING}`),
  },
  {
    key: WorkloadType.WORKSPACE,
    label: t(`type.${WorkloadType.WORKSPACE}`),
  },
  {
    key: WorkloadType.CUSTOM,
    label: t(`type.${WorkloadType.CUSTOM}`),
  },
];

export const getWorkloadStatusFilterItems = (
  t: (key: string) => string,
): WorkloadFilterItem[] => [
  {
    key: WorkloadStatus.PENDING,
    label: t(`status.${WorkloadStatus.PENDING}`),
  },
  {
    key: WorkloadStatus.RUNNING,
    label: t(`status.${WorkloadStatus.RUNNING}`),
  },
  {
    key: WorkloadStatus.TERMINATED,
    label: t(`status.${WorkloadStatus.TERMINATED}`),
  },
  {
    key: WorkloadStatus.COMPLETE,
    label: t(`status.${WorkloadStatus.COMPLETE}`),
  },
  {
    key: WorkloadStatus.FAILED,
    label: t(`status.${WorkloadStatus.FAILED}`),
  },
  {
    key: WorkloadStatus.UNKNOWN,
    label: t(`status.${WorkloadStatus.UNKNOWN}`),
  },
  {
    key: WorkloadStatus.DELETING,
    label: t(`status.${WorkloadStatus.DELETING}`),
  },
  {
    key: WorkloadStatus.DELETE_FAILED,
    label: t(`status.${WorkloadStatus.DELETE_FAILED}`),
    showDivider: true,
  },
  {
    key: WorkloadStatus.DELETED,
    label: t(`status.${WorkloadStatus.DELETED}`),
  },
];

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
};

export const getWorkloadStatusVariants = (
  t: (key: string) => string,
): Record<WorkloadStatus, StatusBadgeVariant> => ({
  [WorkloadStatus.COMPLETE]: {
    label: t(`status.${WorkloadStatus.COMPLETE}`),
    intent: Intent.SUCCESS,
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
  [WorkloadStatus.UNKNOWN]: {
    label: t(`status.${WorkloadStatus.UNKNOWN}`),
    icon: IconQuestionMark,
    color: 'danger',
  },
});

export default getWorkloadStatusVariants;
