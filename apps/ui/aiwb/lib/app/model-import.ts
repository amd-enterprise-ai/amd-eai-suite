// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { APIRequestError, getErrorMessage } from '@amdenterpriseai/utils/app';

import type {
  ModelOnboardRequest,
  ModelOnboardingStatusResponse,
  ModelSourcePreviewRequest,
  ModelSourcePreviewResponse,
} from '@/types/model-import';

function parseJsonEnvelope<T>(json: unknown): T {
  if (json && typeof json === 'object' && 'data' in json) {
    return (json as { data: T }).data;
  }
  return json as T;
}

function isNoContentProxyResponse(json: unknown): boolean {
  return (
    json !== null &&
    typeof json === 'object' &&
    'status' in json &&
    (json as { status: number }).status === 204
  );
}

/**
 * Resolves a Hugging Face reference into metadata and candidate weight files.
 *
 * Calls the BFF at `POST /api/projects/{project}/models/preview`, which
 * proxies to the upstream AIWB endpoint
 * `POST /v1/projects/{project_name}/models/preview`.
 */
export async function previewModelSource(
  projectName: string,
  body: ModelSourcePreviewRequest,
): Promise<ModelSourcePreviewResponse> {
  if (!projectName.trim()) {
    throw new APIRequestError('No project selected', 422);
  }
  if (!body.source?.trim()) {
    throw new APIRequestError('Model source is required', 422);
  }
  const response = await fetch(
    `/api/projects/${encodeURIComponent(projectName)}/models/preview`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to preview model source: ${errorMessage}`,
      response.status,
    );
  }
  const json: unknown = await response.json();
  return parseJsonEnvelope<ModelSourcePreviewResponse>(json);
}

/**
 * Persists a previewed Hugging Face source with the selected runtime profile.
 *
 * Calls the BFF at `POST /api/projects/{project}/models/onboard`, which
 * proxies to the upstream AIWB endpoint
 * `POST /v1/projects/{project_name}/models/onboard`. The upstream endpoint
 * responds with 204 No Content on success.
 */
export async function onboardModel(
  projectName: string,
  body: ModelOnboardRequest,
): Promise<void> {
  if (!projectName.trim()) {
    throw new APIRequestError('No project selected', 422);
  }
  if (!body.repoId?.trim()) {
    throw new APIRequestError('Model repo id is required', 422);
  }
  if (!body.revision?.trim()) {
    throw new APIRequestError('Model revision is required', 422);
  }
  if (!body.sha?.trim()) {
    throw new APIRequestError('Model sha is required', 422);
  }
  if (!body.displayName?.trim()) {
    throw new APIRequestError('Model display name is required', 422);
  }
  if (!body.image?.trim()) {
    throw new APIRequestError('Container image is required', 422);
  }
  const response = await fetch(
    `/api/projects/${encodeURIComponent(projectName)}/models/onboard`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to start model onboarding: ${errorMessage}`,
      response.status,
    );
  }
  if (response.status === 204) {
    return;
  }
  const json: unknown = await response.json();
  if (isNoContentProxyResponse(json)) {
    return;
  }
}

/**
 * Polls onboarding progress for a model created via {@link onboardModel}.
 *
 * Calls the BFF at `GET /api/projects/{project}/models/{modelId}/onboarding`,
 * which proxies to the upstream AIWB endpoint
 * `GET /v1/projects/{project_name}/models/{model_id}/onboarding`.
 */
export async function getModelOnboardingStatus(
  projectName: string,
  modelId: string,
): Promise<ModelOnboardingStatusResponse> {
  if (!projectName.trim()) {
    throw new APIRequestError('No project selected', 422);
  }
  if (!modelId.trim()) {
    throw new APIRequestError('Model id is required', 422);
  }
  const response = await fetch(
    `/api/projects/${encodeURIComponent(projectName)}/models/${encodeURIComponent(modelId)}/onboarding`,
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch model onboarding status: ${errorMessage}`,
      response.status,
    );
  }
  const json: unknown = await response.json();
  return parseJsonEnvelope<ModelOnboardingStatusResponse>(json);
}
