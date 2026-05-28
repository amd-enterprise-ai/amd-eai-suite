// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  ADVANCED_PARAM_AUTOMATIC,
  filterProfilesByAdvancedParams,
} from '@/lib/app/aims/filterProfilesByAdvancedParams';
import {
  AIMClusterServiceTemplate,
  AIMMetric,
  AIM_PROFILE_TYPE_OPTIMIZED,
} from '@/types/aims';

function makeTemplate(
  name: string,
  meta: NonNullable<AIMClusterServiceTemplate['status']['profile']>['metadata'],
  specMetric: AIMMetric.Latency | AIMMetric.Throughput = AIMMetric.Latency,
): AIMClusterServiceTemplate {
  return {
    metadata: { name, labels: {} },
    spec: { modelName: 'test-model', metric: specMetric },
    status: {
      status: 'Ready',
      profile: { metadata: meta },
    },
  };
}

const automatic = {
  selectedMetric: undefined,
  optimizationClass: ADVANCED_PARAM_AUTOMATIC,
  gpuModel: ADVANCED_PARAM_AUTOMATIC,
  precision: ADVANCED_PARAM_AUTOMATIC,
  gpuCount: ADVANCED_PARAM_AUTOMATIC,
};

describe('filterProfilesByAdvancedParams', () => {
  const latencyA = makeTemplate('a', {
    metric: 'latency',
    type: AIM_PROFILE_TYPE_OPTIMIZED,
    gpu: 'MI300X',
    precision: 'fp8',
    gpuCount: 8,
  });
  const latencyB = makeTemplate(
    'b',
    {
      metric: 'latency',
      type: 'unoptimized',
      gpu: 'MI250',
      precision: 'fp16',
      gpuCount: 4,
    },
    AIMMetric.Latency,
  );
  const throughputOnly = makeTemplate(
    'c',
    {
      metric: 'throughput',
      type: AIM_PROFILE_TYPE_OPTIMIZED,
      gpu: 'MI300X',
      precision: 'fp8',
      gpuCount: 8,
    },
    AIMMetric.Throughput,
  );

  it('returns empty when profiles is empty', () => {
    expect(filterProfilesByAdvancedParams([], automatic)).toEqual([]);
  });

  it('keeps all profiles that pass metric when advanced params are all automatic', () => {
    const profiles = [latencyA, latencyB];
    const out = filterProfilesByAdvancedParams(profiles, {
      ...automatic,
      selectedMetric: 'latency',
    });
    expect(out.map((t) => t.metadata.name)).toEqual(['a', 'b']);
  });

  it('excludes templates whose metadata.metric does not match selected metric', () => {
    const profiles = [latencyA, throughputOnly];
    const out = filterProfilesByAdvancedParams(profiles, {
      ...automatic,
      selectedMetric: 'throughput',
    });
    expect(out.map((t) => t.metadata.name)).toEqual(['c']);
  });

  it('excludes templates with no profile metadata when a metric is selected', () => {
    const noMeta: AIMClusterServiceTemplate = {
      metadata: { name: 'x', labels: {} },
      spec: { modelName: 'm', metric: AIMMetric.Latency },
      status: { status: 'Ready' },
    };
    const out = filterProfilesByAdvancedParams([noMeta, latencyA], {
      ...automatic,
      selectedMetric: 'latency',
    });
    expect(out).toEqual([latencyA]);
  });

  it('filters by optimization class when set to a concrete value', () => {
    const profiles = [latencyA, latencyB];
    const out = filterProfilesByAdvancedParams(profiles, {
      ...automatic,
      selectedMetric: 'latency',
      optimizationClass: AIM_PROFILE_TYPE_OPTIMIZED,
    });
    expect(out.map((t) => t.metadata.name)).toEqual(['a']);
  });

  it('filters by gpu when set', () => {
    const out = filterProfilesByAdvancedParams([latencyA, latencyB], {
      ...automatic,
      selectedMetric: 'latency',
      gpuModel: 'MI250',
    });
    expect(out.map((t) => t.metadata.name)).toEqual(['b']);
  });

  it('filters by precision when set', () => {
    const out = filterProfilesByAdvancedParams([latencyA, latencyB], {
      ...automatic,
      selectedMetric: 'latency',
      precision: 'fp16',
    });
    expect(out.map((t) => t.metadata.name)).toEqual(['b']);
  });

  it('filters by gpu count as string compare to metadata.gpuCount', () => {
    const out = filterProfilesByAdvancedParams([latencyA, latencyB], {
      ...automatic,
      selectedMetric: 'latency',
      gpuCount: '8',
    });
    expect(out.map((t) => t.metadata.name)).toEqual(['a']);
  });

  it('treats empty string optimizationClass as automatic (matches type equality via empty string)', () => {
    const preview = makeTemplate('p', {
      metric: 'latency',
      type: 'preview',
      gpu: 'MI300X',
      precision: 'fp8',
      gpuCount: 8,
    });
    const out = filterProfilesByAdvancedParams([latencyA, preview], {
      selectedMetric: 'latency',
      optimizationClass: '',
      gpuModel: ADVANCED_PARAM_AUTOMATIC,
      precision: ADVANCED_PARAM_AUTOMATIC,
      gpuCount: ADVANCED_PARAM_AUTOMATIC,
    });
    expect(out.length).toBe(2);
  });

  it('combines metric with multiple advanced dimensions', () => {
    const out = filterProfilesByAdvancedParams([latencyA, latencyB], {
      selectedMetric: 'latency',
      optimizationClass: AIM_PROFILE_TYPE_OPTIMIZED,
      gpuModel: 'MI300X',
      precision: 'fp8',
      gpuCount: '8',
    });
    expect(out).toEqual([latencyA]);
  });
});
