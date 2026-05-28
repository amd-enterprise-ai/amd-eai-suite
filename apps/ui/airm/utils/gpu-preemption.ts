// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { TFunction } from 'i18next';

import { GpuPreemptionPolicy } from '@/types/enums/gpu-preemption-policy';

/**
 * Maps API policy values to localized strings for read-only UI.
 * Accepts unknown strings so slightly mismatched payloads still show something.
 */
export function gpuPreemptionPolicyDisplayLabel(
  policy: GpuPreemptionPolicy | string | null | undefined,
  t: TFunction,
): string {
  if (policy === GpuPreemptionPolicy.OnPressure) {
    return t('modal.create.form.preemption.policy.onPressure');
  }
  if (policy === GpuPreemptionPolicy.Always) {
    return t('modal.create.form.preemption.policy.always');
  }
  if (policy == null || policy === '') {
    return '—';
  }
  return String(policy);
}

/**
 * Formats API grace period (seconds) for read-only UI as whole minutes plus suffix.
 */
export function formatGpuPreemptionIdleTimerFromSeconds(
  gracePeriodSeconds: number | null | undefined,
  t: TFunction,
): string {
  const suffix = t('modal.create.form.preemption.gracePeriod.suffix');
  if (gracePeriodSeconds == null || !Number.isFinite(gracePeriodSeconds)) {
    return '—';
  }
  const minutes = Math.floor(gracePeriodSeconds / 60);
  return `${minutes} ${suffix}`;
}

/**
 * Read-only GPU activity threshold (`GpuPreemptionConfig.threshold`).
 * Backend may omit or null partial fields even when pre-emption is enabled.
 */
export function formatGpuPreemptionThresholdPercent(
  threshold: number | null | undefined,
): string {
  if (threshold == null || !Number.isFinite(threshold)) {
    return '—';
  }
  return `${threshold}%`;
}
