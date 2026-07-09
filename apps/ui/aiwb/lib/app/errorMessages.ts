// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ErrorCodes } from '@amdenterpriseai/types';
import type { commonKeys } from '@/types/react-i18next';
import { translationKeyGenerator } from './i18n';

const ERROR_TITLE_KEYS = {
  [ErrorCodes.NO_SUBMITTABLE_PROJECTS]: 'error.noSubmittableProjects.title',
  [ErrorCodes.FETCH_FAILED]: 'error.fetchFailed.title',
  [ErrorCodes.SERVICE_ERROR]: 'error.service.title',
  [ErrorCodes.PROJECT_NOT_FOUND]: 'error.projectNotFound.title',
} as const satisfies Partial<Record<ErrorCodes, commonKeys>>;

const ERROR_DESCRIPTION_KEYS = {
  [ErrorCodes.NO_SUBMITTABLE_PROJECTS]:
    'error.noSubmittableProjects.description',
  [ErrorCodes.FETCH_FAILED]: 'error.fetchFailed.description',
  [ErrorCodes.SERVICE_ERROR]: 'error.service.description',
  [ErrorCodes.PROJECT_NOT_FOUND]: 'error.projectNotFound.description',
} as const satisfies Partial<Record<ErrorCodes, commonKeys>>;

export const getErrorTitleTranslationKey =
  translationKeyGenerator(ERROR_TITLE_KEYS);
export const getErrorDescriptionTranslationKey = translationKeyGenerator(
  ERROR_DESCRIPTION_KEYS,
);
