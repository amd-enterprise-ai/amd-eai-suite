// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

/** Stable catalog key for the automatic image family from GET /cluster/aim-images. */
export const AUTOMATIC_IMAGE_FAMILY_ID = 'automatic';

/**
 * Runtime profile overrides aligned with v1alpha2 AIMProfile.spec fields used
 * by the custom-model onboard wizard.
 */
export type RuntimeProfileOverrides = {
  imageFamilyId: string;
  image?: string;
  acceleratorType: string;
  acceleratorModel: string;
  acceleratorCount: number;
  precision: string;
  engineArgsYaml?: string;
  envVarsYaml?: string;
};

export type RuntimeProfileSelectOption = {
  key: string;
  label: string;
};
