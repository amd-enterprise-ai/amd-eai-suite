// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { TFunction } from 'i18next';
import { z } from 'zod';

import { CREATE_PROJECT_GPU_PREEMPTION_DEFAULTS } from '@/components/features/projects/constants';
import { GpuPreemptionPolicy } from '@/types/enums/gpu-preemption-policy';
import { ProjectGpuPreemptionFormFields } from '@/types/enums/project-form-fields';
import type {
  CreateProjectFormData,
  GpuPreemptionConfig,
} from '@/types/projects';
import { GPU_PREEMPTION_DISABLED } from '@/types/projects';

/** Maps API pre-emption config into create-project form field values. */
export function gpuPreemptionConfigToFormFields(
  config: GpuPreemptionConfig,
): Pick<
  CreateProjectFormData,
  | ProjectGpuPreemptionFormFields.ENABLED
  | ProjectGpuPreemptionFormFields.POLICY
  | ProjectGpuPreemptionFormFields.THRESHOLD
  | ProjectGpuPreemptionFormFields.GRACE_PERIOD
> {
  if (!config.enabled) {
    return {
      [ProjectGpuPreemptionFormFields.ENABLED]: false,
      [ProjectGpuPreemptionFormFields.POLICY]:
        CREATE_PROJECT_GPU_PREEMPTION_DEFAULTS.policy,
      [ProjectGpuPreemptionFormFields.THRESHOLD]:
        CREATE_PROJECT_GPU_PREEMPTION_DEFAULTS.threshold,
      [ProjectGpuPreemptionFormFields.GRACE_PERIOD]:
        CREATE_PROJECT_GPU_PREEMPTION_DEFAULTS.gracePeriod,
    };
  }
  // Whole minutes in the form; floor matches formatGpuPreemptionIdleTimerFromSeconds.
  // API enforces grace_period as a multiple of 60; other values cannot round-trip here.
  const graceMinutes =
    config.gracePeriod != null
      ? Math.floor(config.gracePeriod / 60)
      : CREATE_PROJECT_GPU_PREEMPTION_DEFAULTS.gracePeriod;
  return {
    [ProjectGpuPreemptionFormFields.ENABLED]: true,
    [ProjectGpuPreemptionFormFields.POLICY]: config.policy,
    [ProjectGpuPreemptionFormFields.THRESHOLD]: config.threshold,
    [ProjectGpuPreemptionFormFields.GRACE_PERIOD]: graceMinutes,
  };
}

/** Builds the API `gpuPreemption` object from validated create/settings form data. */
export function gpuPreemptionConfigFromFormData(
  data: CreateProjectFormData,
): GpuPreemptionConfig {
  if (!data[ProjectGpuPreemptionFormFields.ENABLED]) {
    return GPU_PREEMPTION_DISABLED;
  }
  const graceMinutes = data[
    ProjectGpuPreemptionFormFields.GRACE_PERIOD
  ] as number;
  return {
    enabled: true,
    threshold: data[ProjectGpuPreemptionFormFields.THRESHOLD] as number,
    gracePeriod: graceMinutes * 60,
    policy: data[ProjectGpuPreemptionFormFields.POLICY] as GpuPreemptionPolicy,
  };
}

/**
 * Zod superRefine for GPU pre-emption fields when the toggle is on.
 * Shared by create-project and project settings so validation messages stay aligned.
 */
export function refineGpuPreemptionFormData(
  data: CreateProjectFormData,
  ctx: z.RefinementCtx,
  t: TFunction,
): void {
  if (!data[ProjectGpuPreemptionFormFields.ENABLED]) {
    return;
  }
  const policy = data[ProjectGpuPreemptionFormFields.POLICY];
  if (policy == null || !Object.values(GpuPreemptionPolicy).includes(policy)) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: t('modal.create.form.preemption.validation.policyRequired'),
      path: [ProjectGpuPreemptionFormFields.POLICY],
    });
  }
  const th = data[ProjectGpuPreemptionFormFields.THRESHOLD];
  if (
    th === undefined ||
    !Number.isFinite(th) ||
    !Number.isInteger(th) ||
    th < 0 ||
    th > 100
  ) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: t('modal.create.form.preemption.validation.thresholdRange'),
      path: [ProjectGpuPreemptionFormFields.THRESHOLD],
    });
  }
  const gr = data[ProjectGpuPreemptionFormFields.GRACE_PERIOD];
  if (
    gr === undefined ||
    !Number.isFinite(gr) ||
    !Number.isInteger(gr) ||
    gr < 15
  ) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: t('modal.create.form.preemption.validation.graceMin'),
      path: [ProjectGpuPreemptionFormFields.GRACE_PERIOD],
    });
  }
}
