// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { StatusBadgeVariant } from '@amdenterpriseai/types';
import { ModelOnboardingStatus } from '@/types/models';
import { Intent } from '@amdenterpriseai/types';

export const getModelStatusVariants = (
  t: (key: string) => string,
): Record<ModelOnboardingStatus, StatusBadgeVariant> => ({
  [ModelOnboardingStatus.READY]: {
    label: t('status.ready'),
    intent: Intent.SUCCESS,
  },
  [ModelOnboardingStatus.FAILED]: {
    label: t('status.failed'),
    intent: Intent.DANGER,
  },
  [ModelOnboardingStatus.PENDING]: {
    label: t('status.pending'),
    intent: Intent.PENDING,
  },
});

export default getModelStatusVariants;
