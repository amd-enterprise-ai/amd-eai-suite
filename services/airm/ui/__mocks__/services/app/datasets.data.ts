// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { DatasetType } from '@/types/datasets';

export const mockDatasets = [
  {
    id: '1',
    name: 'dataset-1',
    description: 'Dataset for evaluation',
    type: DatasetType.Evaluation,
    createdAt: '2023-01-01T00:00:00Z',
    updatedAt: '2023-01-01T00:00:00Z',
  },
  {
    id: '2',
    name: 'dataset-2',
    description: 'Dataset for fine-tuning',
    type: DatasetType.Finetuning,
    createdAt: '2023-01-02T00:00:00Z',
    updatedAt: '2023-01-02T00:00:00Z',
  },
];
