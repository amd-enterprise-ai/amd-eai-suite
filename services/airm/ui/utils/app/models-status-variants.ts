// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { StatusBadgeVariant } from '@/types/data-table/status-variant';
import { ModelOnboardingStatus } from '@/types/models';
import { Intent } from '@/components/shared/Status/Status';

export const getModelStatusVariants = (
  t: (key: string) => string,
): Record<ModelOnboardingStatus, StatusBadgeVariant> => ({
  [ModelOnboardingStatus.READY]: {
    label: t(`status.${ModelOnboardingStatus.READY}`),
    intent: Intent.SUCCESS,
  },
  [ModelOnboardingStatus.FAILED]: {
    label: t(`status.${ModelOnboardingStatus.FAILED}`),
    intent: Intent.DANGER,
  },
  [ModelOnboardingStatus.PENDING]: {
    label: t(`status.${ModelOnboardingStatus.PENDING}`),
    intent: Intent.PENDING,
  },
});

export default getModelStatusVariants;
