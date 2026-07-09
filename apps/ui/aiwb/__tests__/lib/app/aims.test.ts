// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { describe, expect, it } from 'vitest';

import { resolveBaseModelSource } from '@/lib/app/aims';
import type { AIMClusterModel, AIMModel } from '@/types/aims';

const baseModel = (spec: AIMModel['spec']): AIMModel => ({
  metadata: { name: 'ft-1', creationTimestamp: '2026-01-01T00:00:00Z' },
  spec,
  status: { status: 'Ready' },
});

describe('resolveBaseModelSource', () => {
  it('reads the legacy flat spec.modelSources when present', () => {
    const model = baseModel({
      modelSources: [{ modelId: 'org/base', sourceUri: 's3://bucket/base' }],
    });
    expect(resolveBaseModelSource(model)).toEqual({
      modelId: 'org/base',
      sourceUri: 's3://bucket/base',
    });
  });

  it('falls back to the v1alpha2 profile override modelSources', () => {
    const model = baseModel({
      profiles: {
        overrides: {
          modelSources: [
            { modelId: 'org/override', sourceUri: 's3://bucket/override' },
          ],
        },
      },
    });
    expect(resolveBaseModelSource(model)).toEqual({
      modelId: 'org/override',
      sourceUri: 's3://bucket/override',
    });
  });

  it('prefers the flat field over the profile override when both exist', () => {
    const model = baseModel({
      modelSources: [{ modelId: 'org/flat', sourceUri: 's3://bucket/flat' }],
      profiles: {
        overrides: {
          modelSources: [
            { modelId: 'org/override', sourceUri: 's3://bucket/override' },
          ],
        },
      },
    });
    expect(resolveBaseModelSource(model)?.modelId).toBe('org/flat');
  });

  it('returns null when neither source field is populated', () => {
    expect(resolveBaseModelSource(baseModel({}))).toBeNull();
  });

  it('returns null for cluster models, which carry no weights source', () => {
    const clusterModel = {
      metadata: { name: 'cluster-aim' },
      spec: { image: 'amdenterpriseai/aim-base:0.10' },
      status: { status: 'Ready' },
    } as unknown as AIMClusterModel;
    expect(resolveBaseModelSource(clusterModel)).toBeNull();
  });
});
