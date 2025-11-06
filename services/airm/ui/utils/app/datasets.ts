// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ChipDisplayVariant } from '@/types/data-table/chip-variant';
import { DatasetType } from '@/types/datasets';

export const DATASET_FILESIZE_LIMIT = 100 * 1024 * 1024; // 100MB

export const getDatasetTypeVariants = (
  t: (key: string) => string,
): Record<DatasetType, ChipDisplayVariant> => ({
  [DatasetType.Finetuning]: {
    label: t(`types.${DatasetType.Finetuning}`),
    color: 'warning',
  },
  [DatasetType.Evaluation]: {
    label: t(`types.${DatasetType.Evaluation}`),
    color: 'secondary',
  },
});

export default getDatasetTypeVariants;
