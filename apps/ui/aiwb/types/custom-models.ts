// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

/** Lifecycle phase of a custom model — mirrors backend OnboardPhase enum. */
export type OnboardPhase = 'Pending' | 'Importing' | 'Ready' | 'Failed';

/** Composed lifecycle status returned by the custom models API. */
export type CustomModelOnboardStatus = {
  state: OnboardPhase;
  status: string;
  templateReady: boolean;
  artifactPhase: string | null;
  artifactLastError: string | null;
};

/**
 * Custom model as returned by GET /v1/projects/{project}/models.
 *
 * Mirrors the backend CustomModelResponse schema (camelCase wire format).
 * Metadata annotations carry display name, description, and tags since
 * AIMModelSpec does not have dedicated fields for those.
 */
export type CustomModel = {
  metadata: {
    name: string;
    namespace: string;
    uid?: string;
    labels: Record<string, string>;
    annotations: Record<string, string>;
    creationTimestamp: string;
  };
  spec: {
    aimId: string | null;
    image: string;
    modelSources: { modelId: string; sourceUri: string }[];
    profiles: {
      overrides?: {
        image?: string | null;
        modelSources?: {
          modelId?: string;
          sourceUri?: string;
          env?: { name: string }[];
        }[];
        // Runtime knobs the onboard/edit flow may stamp into overrides. Omitted
        // on older imports or minimal payloads; prefill then falls back to the
        // catalog (see profileOverridesToFormValues).
        imageFamilyId?: string;
        acceleratorType?: string;
        acceleratorModel?: string;
        acceleratorCount?: number;
        precision?: string;
        engineArgs?: Record<string, unknown> | null;
        engineEnv?: Record<string, string> | null;
        // Legacy YAML-string fields from earlier imports; read-back falls back
        // to these when the canonical engineArgs/engineEnv are absent.
        engineArgsYaml?: string;
        envVarsYaml?: string;
      } | null;
    } | null;
  };
  /** Composed onboarding lifecycle status. */
  phase: CustomModelOnboardStatus;
  status: unknown;
  /** AIMProfile resource joined by the backend; null until aim-engine emits it. */
  profile: unknown | null;
};

/** List envelope returned by the backend for custom models. */
export type CustomModelListResponse = {
  data: CustomModel[];
};

/**
 * Runtime matrix a custom (BYOM) model will support in a project, derived from
 * the namespace base-image model's base-role AIMProfiles. Mirrors the backend
 * RuntimeProfileOptions schema (camelCase wire format).
 *
 * The onboard wizard uses these to preset and constrain its runtime selectors
 * — most importantly precision, which the AIMModel CRD prunes when sent freely
 * and is therefore base-determined rather than user-chosen. Empty arrays mean
 * the base model has not emitted profiles yet, so the wizard falls back to its
 * static defaults.
 */
export type RuntimeProfileOptions = {
  acceleratorModels: string[];
  precisions: string[];
  acceleratorCounts: number[];
  optimizationClasses: string[];
};

/**
 * Partial-update body for PATCH /v1/projects/{project}/models/{modelId},
 * mirroring the backend CustomModelPatchRequest (camelCase wire format).
 *
 * Supply only the fields to change. Display metadata (`displayName` /
 * `description` / `tags`) patches the AIMModel annotations. A runtime-profile
 * edit (`image` + `customProfile`) rewrites `spec.profiles.overrides` and
 * repatches the live AIMProfile; merge-patch semantics apply, so the client
 * must send the complete desired profile (a `null` value resets that field to
 * the aim-engine default). `customProfile` is opaque to the API, hence the
 * loose record type.
 */
export type CustomModelPatchBody = {
  displayName?: string;
  description?: string;
  tags?: string[];
  image?: string;
  customProfile?: Record<string, unknown>;
};
