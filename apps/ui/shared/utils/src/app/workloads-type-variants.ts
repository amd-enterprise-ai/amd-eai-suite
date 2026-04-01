// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ChipDisplayVariant } from '@amdenterpriseai/types';
import { WorkloadType } from '@amdenterpriseai/types';

export const getWorkloadTypeVariants = (
  t: (key: string) => string,
): Record<WorkloadType, ChipDisplayVariant> => ({
  [WorkloadType.MODEL_DOWNLOAD]: {
    label: t(`type.${WorkloadType.MODEL_DOWNLOAD}`),
    color: 'default',
  },
  [WorkloadType.INFERENCE]: {
    label: t(`type.${WorkloadType.INFERENCE}`),
    color: 'primary',
  },
  [WorkloadType.FINE_TUNING]: {
    label: t(`type.${WorkloadType.FINE_TUNING}`),
    color: 'warning',
  },
  [WorkloadType.WORKSPACE]: {
    label: t(`type.${WorkloadType.WORKSPACE}`),
    color: 'success',
  },
  [WorkloadType.CUSTOM]: {
    label: t(`type.${WorkloadType.CUSTOM}`),
    color: 'default',
  },
});

export default getWorkloadTypeVariants;
