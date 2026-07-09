// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { ModelOnboardingStatus } from '@/types/models';

/**
 * Coarse role classification produced by the backend preview endpoint.
 * `primary` / `shard` files are selectable weight blobs; `config` files
 * (tokenizer/README/config.json) are returned for context only.
 */
export type ModelSourceWeightFileRole = 'primary' | 'shard' | 'config';

export interface ModelSourceWeightFile {
  path: string;
  sizeBytes?: number | null;
  /**
   * Known classification, or an unrecognized string when the backend adds
   * a new role we haven't modeled yet. `(string & {})` keeps the literal
   * union autocomplete-friendly while still allowing forward-compatible
   * values at runtime.
   */
  role?: ModelSourceWeightFileRole | (string & {}) | null;
}

/** Preview request body sent by the wizard's "Model source" step. */
export interface ModelSourcePreviewRequest {
  source: string;
  /** Kubernetes secret name in the project (HF token); not echoed back. */
  hfTokenSecretName?: string;
}

/** Preview success body returned by the BFF (envelope unwrapped). */
export interface ModelSourcePreviewResponse {
  repoId: string;
  revision: string;
  sha: string;
  displayName: string;
  description: string;
  tags: string[];
  pipelineTag?: string | null;
  gated: boolean;
  hfTokenRecommended: boolean;
  weightFiles: ModelSourceWeightFile[];
  layoutHint?: string | null;
}

/**
 * Runtime profile overrides forwarded on onboard using v1alpha2 AIMProfile.spec
 * field names. Today this travels on `customProfile`; the API may later accept
 * nested `profiles.overrides` directly.
 */
export interface ModelCustomProfile {
  imageFamilyId?: string;
  image?: string;
  acceleratorType?: string;
  acceleratorModel?: string;
  acceleratorCount?: number;
  precision?: string;
  /** Inference-engine CLI args as a free-form object (aim-engine `engineArgs`). */
  engineArgs?: Record<string, unknown>;
  /**
   * Inference-engine env vars as `[{name, value}]` entries. Env var names are
   * UPPER_SNAKE_CASE, so they ride as values (not keys) to stay outside the
   * camelCase contract; the server collapses them into the aim-engine
   * `engineEnv` map.
   */
  engineEnv?: EngineEnvEntry[];
}

/** A single inference-engine environment variable as a name/value pair. */
export interface EngineEnvEntry {
  name: string;
  value: string;
}

/**
 * Onboard request body for POST `/projects/{project}/models/onboard`.
 * Hub-validated fields come from preview; `image` and optional
 * `customProfile` come from the runtime step.
 */
export interface ModelOnboardRequest {
  repoId: string;
  revision: string;
  sha: string;
  displayName: string;
  description?: string;
  tags?: string[];
  image: string;
  hfTokenSecretName?: string;
  customProfile?: ModelCustomProfile;
}

/** Onboarding status response (envelope unwrapped). */
export interface ModelOnboardingStatusResponse {
  onboardingStatus: ModelOnboardingStatus;
  phase?: string;
  percentComplete?: number;
  lastError?: string | null;
  modelWeightsPath?: string | null;
}
