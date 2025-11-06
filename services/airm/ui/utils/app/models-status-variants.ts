// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { IconCircleCheck, IconCircleX } from '@tabler/icons-react';

import { StatusBadgeVariant } from '@/types/data-table/status-variant';
import { ModelOnboardingStatus } from '@/types/models';

export const getModelStatusVariants = (
  t: (key: string) => string,
): Record<ModelOnboardingStatus, StatusBadgeVariant> => ({
  [ModelOnboardingStatus.READY]: {
    label: t(`status.${ModelOnboardingStatus.READY}`),
    icon: IconCircleCheck,
    color: 'success',
  },
  [ModelOnboardingStatus.FAILED]: {
    label: t(`status.${ModelOnboardingStatus.FAILED}`),
    icon: IconCircleX,
    color: 'danger',
  },
  [ModelOnboardingStatus.PENDING]: {
    label: t(`status.${ModelOnboardingStatus.PENDING}`),
    icon: 'spinner',
    color: 'primary',
  },
});

export default getModelStatusVariants;
