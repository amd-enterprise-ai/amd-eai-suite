// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  formatGpuPreemptionIdleTimerFromSeconds,
  formatGpuPreemptionThresholdPercent,
  gpuPreemptionPolicyDisplayLabel,
} from '@/utils/gpu-preemption';
import { GpuPreemptionPolicy } from '@/types/enums/gpu-preemption-policy';
import type { TFunction } from 'i18next';
import { vi } from 'vitest';

const t = vi.fn((key: string) => {
  if (key === 'modal.create.form.preemption.gracePeriod.suffix') {
    return 'min';
  }
  if (key === 'modal.create.form.preemption.policy.onPressure') {
    return 'During GPU pressure';
  }
  if (key === 'modal.create.form.preemption.policy.always') {
    return 'Always active';
  }
  return key;
}) as unknown as TFunction;

describe('gpuPreemptionPolicyDisplayLabel', () => {
  it('maps OnPressure and Always', () => {
    expect(
      gpuPreemptionPolicyDisplayLabel(GpuPreemptionPolicy.OnPressure, t),
    ).toBe('During GPU pressure');
    expect(gpuPreemptionPolicyDisplayLabel(GpuPreemptionPolicy.Always, t)).toBe(
      'Always active',
    );
  });

  it('returns em dash for nullish policy', () => {
    expect(gpuPreemptionPolicyDisplayLabel(null, t)).toBe('—');
    expect(gpuPreemptionPolicyDisplayLabel(undefined, t)).toBe('—');
  });

  it('returns unknown policy string as-is', () => {
    expect(gpuPreemptionPolicyDisplayLabel('FuturePolicy', t)).toBe(
      'FuturePolicy',
    );
  });
});

describe('formatGpuPreemptionIdleTimerFromSeconds', () => {
  it('formats API seconds as whole minutes with suffix', () => {
    expect(formatGpuPreemptionIdleTimerFromSeconds(1800, t)).toBe('30 min');
    expect(formatGpuPreemptionIdleTimerFromSeconds(0, t)).toBe('0 min');
    expect(formatGpuPreemptionIdleTimerFromSeconds(90, t)).toBe('1 min');
  });

  it('returns em dash for nullish or non-finite values', () => {
    expect(formatGpuPreemptionIdleTimerFromSeconds(null, t)).toBe('—');
    expect(formatGpuPreemptionIdleTimerFromSeconds(undefined, t)).toBe('—');
    expect(formatGpuPreemptionIdleTimerFromSeconds(Number.NaN, t)).toBe('—');
    expect(
      formatGpuPreemptionIdleTimerFromSeconds(Number.POSITIVE_INFINITY, t),
    ).toBe('—');
  });
});

describe('formatGpuPreemptionThresholdPercent', () => {
  it('formats finite thresholds with percent suffix', () => {
    expect(formatGpuPreemptionThresholdPercent(72)).toBe('72%');
    expect(formatGpuPreemptionThresholdPercent(0)).toBe('0%');
  });

  it('returns em dash for nullish or non-finite values', () => {
    expect(formatGpuPreemptionThresholdPercent(null)).toBe('—');
    expect(formatGpuPreemptionThresholdPercent(undefined)).toBe('—');
    expect(formatGpuPreemptionThresholdPercent(Number.NaN)).toBe('—');
    expect(formatGpuPreemptionThresholdPercent(Number.POSITIVE_INFINITY)).toBe(
      '—',
    );
  });
});
