// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { APIRequestError, getErrorMessage } from '@amdenterpriseai/utils/app';

import { AggregatedAIM, AIMWorkloadStatus, ParsedAIM } from '@/types/aims';
import {
  CustomModel,
  CustomModelListResponse,
  CustomModelPatchBody,
  RuntimeProfileOptions,
} from '@/types/custom-models';

/** Thrown when DELETE custom model returns 409; carries blocking AIMService names when the API provides them. */
export class CustomModelDeleteConflictError extends APIRequestError {
  readonly blockingServices: string[];

  constructor(message: string, blockingServices: string[]) {
    super(message, 409);
    this.name = 'CustomModelDeleteConflictError';
    this.blockingServices = blockingServices;
  }
}

// Annotation keys stamped by the backend onboarding flow.
// Must stay in sync with apps/api/aiwb/app/custom_models/constants.py.
const MODEL_DISPLAY_NAME_ANNOTATION =
  'aiwb.apps.eai.amd.com/model-display-name';
const CANONICAL_REPO_ID_ANNOTATION = 'aiwb.apps.eai.amd.com/canonical-repo-id';
const SOURCE_DESCRIPTION_ANNOTATION =
  'aiwb.apps.eai.amd.com/source-description';
const SOURCE_TAGS_ANNOTATION = 'aiwb.apps.eai.amd.com/source-tags';
const REVISION_ANNOTATION = 'airm.silogen.ai/revision';

function parseTags(raw: string | undefined): string[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

/**
 * Extracts the organisation name from a HuggingFace repo ID.
 *
 * e.g. "meta-llama/Llama-3.2-1B-Instruct" → "meta-llama"
 */
function extractOrgName(repoId: string): string {
  return repoId.split('/')[0] ?? repoId;
}

/**
 * Maps a single CustomModel API response to an AggregatedAIM so the existing
 * CustomModelCard component can render it without changes.
 *
 * Each custom model CR is its own family (one version per card). The repository
 * key is the CR metadata name so cards remain stable across refreshes.
 */
export function customModelToAggregatedAIM(model: CustomModel): AggregatedAIM {
  const annotations = model.metadata.annotations ?? {};

  const displayName =
    annotations[MODEL_DISPLAY_NAME_ANNOTATION] ?? model.metadata.name;
  const canonicalName =
    annotations[CANONICAL_REPO_ID_ANNOTATION] ?? model.metadata.name;
  const description = annotations[SOURCE_DESCRIPTION_ANNOTATION] ?? '';
  const tags = parseTags(annotations[SOURCE_TAGS_ANNOTATION]);
  // Revision label stamped at onboard time (e.g. "main" or a branch name).
  const revision = annotations[REVISION_ANNOTATION] ?? '';

  // For v1alpha2 onboarded models, image and weight sources live under
  // spec.profiles.overrides rather than the top-level spec fields.
  const overrides = model.spec.profiles?.overrides;
  const firstSource = overrides?.modelSources?.[0];
  const imageReference = overrides?.image ?? model.spec.image ?? '';
  const sourceUri = firstSource?.sourceUri ?? undefined;
  // HF token is wired as a per-source env entry during onboarding; its
  // presence signals that the model requires a token to download weights.
  const isHfTokenRequired = (firstSource?.env ?? []).some(
    (e) => e.name === 'HF_TOKEN',
  );

  const status = model.phase.status;
  // Deployability keys off the composed lifecycle state, not templateReady. An
  // AIMProfile (templateReady) derives from the base image and can exist while
  // the weight import is still running or has failed, so templateReady is true
  // even when the model has no usable weights. Only state==='Ready' means the
  // model is actually deployable.
  const isReady = model.phase.state === 'Ready';

  const parsedAIM: ParsedAIM = {
    model: model.metadata.name,
    aimId: model.spec.aimId ?? null,
    imageReference,
    annotations,
    description: { short: description, full: description },
    title: displayName,
    imageVersion: revision,
    canonicalName,
    tags,
    status,
    workloadStatuses: [],
    isPreview: false,
    isHfTokenRequired,
    isCustomImport: true,
    sourceUri,
  };

  const zeroDeploymentCounts = Object.fromEntries(
    Object.values(AIMWorkloadStatus).map((s) => [s, 0]),
  ) as Record<AIMWorkloadStatus, number>;

  return {
    repository: model.metadata.name,
    parsedAIMs: [parsedAIM],
    latestAim: isReady ? parsedAIM : null,
    isSupported: isReady,
    deploymentCounts: zeroDeploymentCounts,
    aggregated: {
      title: displayName,
      aiLabName: extractOrgName(canonicalName),
      canonicalName,
      latestImageVersion: revision,
      isHfTokenRequired,
      isCustomImport: true,
      tags,
      description: { short: description, full: description },
      onboardPhase: model.phase.state,
    },
  };
}

/**
 * Normalizes a custom-model display name for duplicate detection.
 *
 * The onboarding flow keys its dedupe on the display name, so two names that
 * differ only by surrounding whitespace or letter case should be treated as the
 * same when warning the user about an overwrite. This is an advisory comparison
 * for the wizard warning, intentionally broader than the backend's exact
 * label-value collision.
 */
export function normalizeCustomModelDisplayName(name: string): string {
  return name.trim().toLowerCase();
}

/**
 * Builds the set of normalized display names already used by custom models in
 * the project, so the import/edit wizard can warn when a name would overwrite
 * an existing model.
 *
 * @param models - The project's custom models (aggregated card view).
 * @param excludeRepository - In edit mode, the resource name of the model being
 *   edited, so its own current name does not count as a duplicate.
 */
export function collectExistingDisplayNames(
  models: AggregatedAIM[],
  excludeRepository?: string,
): Set<string> {
  const names = new Set<string>();
  for (const model of models) {
    if (excludeRepository && model.repository === excludeRepository) {
      continue;
    }
    const normalized = normalizeCustomModelDisplayName(model.aggregated.title);
    if (normalized) {
      names.add(normalized);
    }
  }
  return names;
}

/** Display metadata for the edit wizard's "Model information" step. */
export type CustomModelDisplayMetadata = {
  displayName: string;
  description: string;
  tags: string[];
};

/**
 * Extracts the editable display metadata (name, description, tags) from a
 * custom model CR's annotations. Used to prefill the edit wizard's step 2;
 * falls back to the CR name when the display-name annotation is absent.
 */
export function extractCustomModelDisplayMetadata(
  model: CustomModel,
): CustomModelDisplayMetadata {
  const annotations = model.metadata.annotations ?? {};
  return {
    displayName:
      annotations[MODEL_DISPLAY_NAME_ANNOTATION] ?? model.metadata.name,
    description: annotations[SOURCE_DESCRIPTION_ANNOTATION] ?? '',
    tags: parseTags(annotations[SOURCE_TAGS_ANNOTATION]),
  };
}

/**
 * Resolves the canonical upstream repo id for a custom model from its
 * annotations, falling back to the CR name. Shown read-only in the edit
 * wizard's source step since the import source is immutable post-onboard.
 */
export function extractCustomModelCanonicalName(model: CustomModel): string {
  const annotations = model.metadata.annotations ?? {};
  return annotations[CANONICAL_REPO_ID_ANNOTATION] ?? model.metadata.name;
}

/**
 * Fetches all custom models for a project from the AIWB API.
 *
 * Backed by GET /api/projects/{project}/models (BFF) →
 * GET /v1/projects/{project}/models (upstream).
 *
 * @param project - The project namespace to list custom models for.
 * @returns Parsed AggregatedAIM list ready for the CustomModels tab.
 * @throws {APIRequestError} If the request fails.
 */
export async function listCustomModels(
  project: string,
): Promise<AggregatedAIM[]> {
  if (!project) {
    throw new APIRequestError('No project selected', 422);
  }

  const response = await fetch(
    `/api/projects/${encodeURIComponent(project)}/models`,
    { method: 'GET', headers: { 'Content-Type': 'application/json' } },
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch custom models: ${errorMessage}`,
      response.status,
    );
  }

  const json: CustomModelListResponse = await response.json();
  return (json.data ?? []).map(customModelToAggregatedAIM);
}

/**
 * Fetches the runtime-profile options a custom model will support in a project.
 *
 * Backed by GET /api/projects/{project}/models/runtime-profile-options (BFF) →
 * GET /v1/projects/{project}/models/runtime-profile-options (upstream). The
 * onboard wizard uses the returned matrix to preset/constrain its runtime
 * selectors. Returns empty arrays when the base model has not emitted profiles
 * yet so callers fall back to static defaults.
 *
 * @throws {APIRequestError} If the project is missing or the request fails.
 */
export async function getRuntimeProfileOptions(
  project: string,
): Promise<RuntimeProfileOptions> {
  if (!project) {
    throw new APIRequestError('No project selected', 422);
  }

  const response = await fetch(
    `/api/projects/${encodeURIComponent(project)}/models/runtime-profile-options`,
    { method: 'GET', headers: { 'Content-Type': 'application/json' } },
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch runtime profile options: ${errorMessage}`,
      response.status,
    );
  }

  const json: unknown = await response.json();
  return unwrapEnvelope<RuntimeProfileOptions>(json);
}

function unwrapEnvelope<T>(json: unknown): T {
  if (json && typeof json === 'object' && 'data' in json) {
    return (json as { data: T }).data;
  }
  return json as T;
}

/**
 * Fetches a single custom model (raw CR + composed status + joined AIMProfile).
 *
 * Backed by GET /api/projects/{project}/models/{modelId} (BFF) →
 * GET /v1/projects/{project}/models/{model_name} (upstream). Returns the raw
 * CR shape — not the aggregated card view — so the edit wizard can prefill from
 * annotations and spec.profiles.overrides.
 *
 * @throws {APIRequestError} If the project/modelId is missing or the request fails.
 */
export async function getCustomModel(
  project: string,
  modelId: string,
): Promise<CustomModel> {
  if (!project) {
    throw new APIRequestError('No project selected', 422);
  }
  if (!modelId) {
    throw new APIRequestError('No model selected', 422);
  }

  const response = await fetch(
    `/api/projects/${encodeURIComponent(project)}/models/${encodeURIComponent(modelId)}`,
    { method: 'GET', headers: { 'Content-Type': 'application/json' } },
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch custom model: ${errorMessage}`,
      response.status,
    );
  }

  const json: unknown = await response.json();
  return unwrapEnvelope<CustomModel>(json);
}

/**
 * Applies a partial update to a custom model (display metadata and/or runtime
 * profile) in one request.
 *
 * Backed by PATCH /api/projects/{project}/models/{modelId} (BFF) →
 * PATCH /v1/projects/{project}/models/{model_name} (upstream). The caller is
 * responsible for sending only changed fields and, for runtime-profile edits,
 * the complete desired profile (merge-patch semantics; see CustomModelPatchBody).
 *
 * @throws {APIRequestError} If the project/modelId/body is missing or the request fails.
 */
export async function patchCustomModel(
  project: string,
  modelId: string,
  body: CustomModelPatchBody,
): Promise<void> {
  if (!project) {
    throw new APIRequestError('No project selected', 422);
  }
  if (!modelId) {
    throw new APIRequestError('No model selected', 422);
  }
  if (Object.keys(body).length === 0) {
    throw new APIRequestError('No changes to save', 422);
  }

  const response = await fetch(
    `/api/projects/${encodeURIComponent(project)}/models/${encodeURIComponent(modelId)}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
  );

  if (!response.ok) {
    let errorMessage = await getErrorMessage(response);
    if (response.status === 405) {
      errorMessage =
        'The server does not support saving these changes. An administrator may need to update the deployment.';
    }
    throw new APIRequestError(
      `Failed to update custom model: ${errorMessage}`,
      response.status,
    );
  }
}

function parseWireErrorJson(text: string): unknown {
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return null;
  }
}

/** Extracts human-readable message from `detail` or BFF `error`, plus optional blocking service names. */
export function parseCustomModelDeleteErrorBody(text: string): {
  detail: string;
  blockingServices: string[];
} {
  const json = parseWireErrorJson(text);
  if (!json || typeof json !== 'object') {
    return { detail: text || 'Request failed', blockingServices: [] };
  }
  const o = json as Record<string, unknown>;
  const detailFromDetail =
    typeof o.detail === 'string' && o.detail.length > 0 ? o.detail : undefined;
  const detailFromError =
    typeof o.error === 'string' && o.error.length > 0 ? o.error : undefined;
  const detail = detailFromDetail ?? detailFromError ?? 'Request failed';
  const info = o.additionalInfo ?? o.additional_info;
  let blockingServices: string[] = [];
  if (Array.isArray(info)) {
    blockingServices = info.filter((x): x is string => typeof x === 'string');
  } else if (info && typeof info === 'object') {
    const d = info as Record<string, unknown>;
    const raw =
      d.blockingServices ??
      d.blockingServiceNames ??
      d.services ??
      d.blockingDeployments;
    if (Array.isArray(raw)) {
      blockingServices = raw.filter((x): x is string => typeof x === 'string');
    }
  }
  return { detail, blockingServices };
}

/**
 * Deletes an onboarded (BYOM) custom model for a project.
 *
 * Backed by DELETE /api/projects/{project}/models/{modelId} (BFF) →
 * DELETE /v1/projects/{project}/models/{model_name} (upstream). Returns on
 * 204 No Content.
 *
 * @throws {CustomModelDeleteConflictError} When the model is still referenced by deployments (409).
 * @throws {APIRequestError} For other failures (including 404).
 */
export async function deleteCustomModel(
  project: string,
  modelName: string,
): Promise<void> {
  if (!project) {
    throw new APIRequestError('No project selected', 422);
  }
  if (!modelName) {
    throw new APIRequestError('No model selected', 422);
  }

  const response = await fetch(
    `/api/projects/${encodeURIComponent(project)}/models/${encodeURIComponent(modelName)}`,
    { method: 'DELETE', headers: { 'Content-Type': 'application/json' } },
  );

  if (response.ok) {
    return;
  }

  const text = await response.text();
  const { detail, blockingServices } = parseCustomModelDeleteErrorBody(text);

  if (response.status === 409) {
    throw new CustomModelDeleteConflictError(detail, blockingServices);
  }

  throw new APIRequestError(
    `Failed to delete custom model: ${detail}`,
    response.status,
  );
}

/**
 * Copies an onboarded custom model in a project.
 *
 * @param project - Project namespace that owns the source model.
 * @param sourceModelName - Source custom-model resource name (`metadata.name`).
 * @throws {APIRequestError} When the copy request fails.
 */
export async function copyCustomModel(
  project: string,
  sourceModelName: string,
): Promise<void> {
  if (!project) {
    throw new APIRequestError('No project selected', 422);
  }
  if (!sourceModelName) {
    throw new APIRequestError('No source custom model name provided', 422);
  }

  const response = await fetch(
    `/api/projects/${encodeURIComponent(project)}/models/${encodeURIComponent(sourceModelName)}/copy`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    },
  );

  if (!response.ok) {
    const errorMessage =
      (await getErrorMessage(response)) ||
      response.statusText ||
      'Request failed';
    throw new APIRequestError(errorMessage, response.status);
  }
}
