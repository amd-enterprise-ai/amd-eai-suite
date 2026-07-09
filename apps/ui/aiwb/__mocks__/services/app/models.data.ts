// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  AIM_MODEL_NAME_LABEL,
  AIM_MODEL_WORKLOAD_ID_LABEL,
  AIMModel,
} from '@/types/aims';

const makeModel = (n: number, extra?: Partial<AIMModel>): AIMModel => ({
  metadata: {
    name: `wb-finetune-cr-${n}`, // K8s auto-generated resource name
    creationTimestamp: '2026-01-01T00:00:00Z',
    labels: {
      [AIM_MODEL_WORKLOAD_ID_LABEL]: String(n),
      [AIM_MODEL_NAME_LABEL]: `model-${n}`, // user-chosen display name
    },
  },
  spec: {
    profiles: {
      overrides: {
        modelSources: [
          { modelId: `org/model-${n}`, sourceUri: `s3://bucket/model-${n}` },
        ],
      },
    },
  },
  status: { status: 'Ready' },
  ...extra,
});

/**
 * Mock data matching the AIMModel item shape inside the ListResponse returned by GET /v1/projects/{project}/fine-tuning/models.
 */
export const mockModels: AIMModel[] = [
  makeModel(1),
  makeModel(2, { status: { status: 'NotReady' } }),
  makeModel(3),
  makeModel(4, { status: { status: 'NotReady' } }),
  makeModel(5),
  makeModel(6),
];
