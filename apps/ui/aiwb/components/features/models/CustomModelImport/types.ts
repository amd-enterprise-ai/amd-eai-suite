// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

/**
 * Field values for the three-step custom model import wizard.
 *
 * A single React Hook Form instance owns this entire object; each step
 * validates and edits its own subset of fields. The shape mirrors
 * {@link import('@/types/model-import').ModelOnboardRequest}; preview fields
 * and the onboard payload are assembled in the wizard host on submit.
 */
export interface CustomModelImportFormValues {
  // Step 1 — Model source
  source: string;
  hfTokenSecretName: string;

  // Step 2 — Model information (display name starts empty per spec)
  displayName: string;
  description: string;
  tagsInput: string;

  // Step 3 — Runtime profile (maps to AIMProfile.spec / profiles.overrides)
  containerImage: string;
  containerVersion: string;
  acceleratorType: string;
  accelerator: string;
  acceleratorCount: number | string;
  modelPrecision: string;
  engineArgsYaml: string;
  envVarsYaml: string;
}

export const DEFAULT_CUSTOM_MODEL_IMPORT_VALUES: CustomModelImportFormValues = {
  source: '',
  hfTokenSecretName: '',
  displayName: '',
  description: '',
  tagsInput: '',
  containerImage: '',
  containerVersion: '',
  acceleratorType: 'gpu',
  accelerator: '',
  acceleratorCount: 1,
  modelPrecision: 'bf16',
  engineArgsYaml: '',
  envVarsYaml: '',
};
