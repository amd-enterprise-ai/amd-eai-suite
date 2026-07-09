// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { APIRequestError, getErrorMessage } from '@amdenterpriseai/utils/app';

import {
  AIMClusterModel,
  AIMDeployPayload,
  AIMService,
  AIMServiceStatus,
  AIMStatus,
  InferenceReplica,
  ParsedAIM,
  UpdateScalingPolicyPayload,
} from '@/types/aims';
import { PaginatedList } from '@/types/pagination';

import { aimParser } from './aims';
import { fetchAllPages } from './pagination';

export interface ListInferenceDeploymentsOptions {
  /**
   * Capability filter. `chat` narrows the list to deployments whose model
   * supports chat completions and whose serving stack is fully ready — the
   * right filter for chat-target pickers.
   */
  capability?: 'chat';
  statusFilter?: AIMServiceStatus[];
}

/**
 * Gets a single base inference model from the cluster catalog by resource name.
 *
 * Backed by GET /v1/inference/models/{name}.
 *
 * @param {string} name - AIMClusterModel metadata.name.
 * @returns {Promise<AIMClusterModel>} The model resource.
 * @throws {APIRequestError} If the API request fails or the name is missing.
 */
export const getInferenceModel = async (
  name: string,
): Promise<AIMClusterModel> => {
  if (!name) {
    throw new APIRequestError('No inference model name provided', 422);
  }

  const response = await fetch(
    `/api/inference/models/${encodeURIComponent(name)}`,
    {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    },
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch inference model: ${errorMessage}`,
      response.status,
    );
  }

  return await response.json();
};

const buildInferenceModelsUrl = (
  page: number,
  pageSize: number,
  statusFilter?: AIMStatus[],
): string => {
  const params = new URLSearchParams();
  params.append('page', String(page));
  params.append('pageSize', String(pageSize));
  statusFilter?.forEach((s) => {
    params.append('statusFilter', s);
  });
  return `/api/inference/models?${params}`;
};

/**
 * Fetches a single page of inference base models from the cluster catalog.
 *
 * Backed by GET /v1/inference/models. Returns the raw paginated envelope so
 * callers can drive UI pagination. `statusFilter` narrows the result set
 * server-side.
 *
 * @param {object} [options] - Optional filters and pagination controls.
 * @returns {Promise<PaginatedList<AIMClusterModel>>} The requested page and pagination metadata.
 * @throws {APIRequestError} If the API request fails.
 */
export const listInferenceModels = async (
  options: {
    page?: number;
    pageSize?: number;
    statusFilter?: AIMStatus[];
  } = {},
): Promise<PaginatedList<AIMClusterModel>> => {
  const { page = 1, pageSize = 10, statusFilter } = options;
  const response = await fetch(
    buildInferenceModelsUrl(page, pageSize, statusFilter),
    {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    },
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch inference models: ${errorMessage}`,
      response.status,
    );
  }
  return await response.json();
};

/**
 * Lists every inference base model in the cluster catalog by walking all pages.
 *
 * Thin wrapper around fetchAllPages — see `apps/ui/aiwb/AGENTS.md`
 * "Paginated list loaders". Returns `[]` on any failure so callers can
 * render an empty state without an error boundary.
 *
 * @param {AIMStatus[]} [statusFilter] - Optional model statuses to filter by.
 * @returns {Promise<AIMClusterModel[]>} All base models matching the filter.
 */
export const listAllInferenceModels = async (
  statusFilter?: AIMStatus[],
): Promise<AIMClusterModel[]> => {
  try {
    return await fetchAllPages<AIMClusterModel>((page, pageSize) =>
      listInferenceModels({ page, pageSize, statusFilter }),
    );
  } catch (error) {
    console.warn('Error fetching inference models:', error);
    return [];
  }
};

/**
 * Deploys a model for inference in the given project.
 *
 * Backed by POST /v1/projects/{project}/inference. The `model` field accepts
 * either a cluster-scoped AIMClusterModel name or a project-scoped fine-tuned
 * AIMModel name; the backend auto-detects.
 *
 * @param {string} project - The project (1:1 with namespace) to deploy in.
 * @param {AIMDeployPayload} payload - Deployment configuration.
 * @returns {Promise<AIMService>} The accepted deployment.
 * @throws {APIRequestError} If the API request fails or the project is missing.
 */
export const deployInference = async (
  project: string,
  payload: AIMDeployPayload,
): Promise<AIMService> => {
  if (!project) {
    throw new APIRequestError('No project selected', 422);
  }

  const response = await fetch(`/api/projects/${project}/inference`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to deploy inference: ${errorMessage}`,
      response.status,
    );
  }

  return response.json();
};

const buildInferenceListUrl = (
  project: string,
  page: number,
  pageSize: number,
  options: ListInferenceDeploymentsOptions,
) => {
  const params = new URLSearchParams();
  params.append('pageSize', String(pageSize));
  params.append('page', String(page));
  if (options.capability) {
    params.append('capability', options.capability);
  }
  options.statusFilter?.forEach((status) => {
    params.append('statusFilter', status);
  });
  return `/api/projects/${project}/inference?${params}`;
};

/**
 * Fetches a single page of inference deployments for a project.
 *
 * Backed by GET /v1/projects/{project}/inference. Returns the raw paginated
 * envelope so callers can drive UI pagination. `capability=chat` narrows the
 * list to deployments whose serving stack is fully ready AND whose model is
 * chat-capable. `statusFilter` further restricts by deployment status and is
 * sent as a repeated `statusFilter` query parameter.
 *
 * @param {string} project - The project (1:1 with namespace) to list in.
 * @param {object} [options] - Optional capability/status filters and pagination controls.
 * @returns {Promise<PaginatedList<AIMService>>} The requested page and pagination metadata.
 * @throws {APIRequestError} If the API request fails.
 */
export const listInferenceDeployments = async (
  project: string,
  options: ListInferenceDeploymentsOptions & {
    page?: number;
    pageSize?: number;
  } = {},
): Promise<PaginatedList<AIMService>> => {
  const { page = 1, pageSize = 10, ...filters } = options;
  const response = await fetch(
    buildInferenceListUrl(project, page, pageSize, filters),
    {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    },
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch inference deployments: ${errorMessage}`,
      response.status,
    );
  }

  return await response.json();
};

/**
 * Lists every inference deployment for a project by walking all pages.
 *
 * Thin wrapper around fetchAllPages — see `apps/ui/aiwb/AGENTS.md`
 * "Paginated list loaders". Returns `[]` on any failure so callers can
 * render an empty state without an error boundary.
 *
 * @param {string} project - The project (1:1 with namespace) to list in.
 * @param {ListInferenceDeploymentsOptions} [options] - Optional capability and status filters.
 * @returns {Promise<AIMService[]>} All inference deployments matching the filters.
 */
export const listAllInferenceDeployments = async (
  project: string,
  options: ListInferenceDeploymentsOptions = {},
): Promise<AIMService[]> => {
  try {
    return await fetchAllPages<AIMService>((page, pageSize) =>
      listInferenceDeployments(project, { ...options, page, pageSize }),
    );
  } catch (error) {
    console.warn('Error fetching inference deployments:', error);
    return [];
  }
};

/**
 * Gets a single inference deployment by ID.
 *
 * Backed by GET /v1/projects/{project}/inference/{id}.
 *
 * @param {string} project - The project (1:1 with namespace).
 * @param {string} id - The UUID of the inference deployment.
 * @returns {Promise<AIMService>} The deployment.
 * @throws {APIRequestError} If the API request fails.
 */
export const getInferenceDeployment = async (
  project: string,
  id: string,
): Promise<AIMService> => {
  const response = await fetch(`/api/projects/${project}/inference/${id}`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch inference deployment: ${errorMessage}`,
      response.status,
    );
  }

  return await response.json();
};

/**
 * Lists per-pod replica info for an inference deployment.
 *
 * Backed by GET /v1/projects/{project}/inference/{id}/replicas. Returns a
 * subset of Kubernetes pod fields (name, phase, IP, containers, resource
 * limits, conditions) for each replica that is currently running.
 *
 * @param {string} project - The project (1:1 with namespace).
 * @param {string} id - The UUID of the inference deployment.
 * @returns {Promise<InferenceReplica[]>} List of per-pod replica info.
 * @throws {APIRequestError} If the API request fails.
 */
export const getInferenceReplicas = async (
  project: string,
  id: string,
): Promise<InferenceReplica[]> => {
  const response = await fetch(
    `/api/projects/${project}/inference/${id}/replicas`,
    {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    },
  );
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch inference replicas: ${errorMessage}`,
      response.status,
    );
  }
  return (await response.json()).data ?? [];
};

/**
 * Updates the scaling policy of an inference deployment.
 *
 * Backed by PATCH /v1/projects/{project}/inference/{id}. All three scaling
 * fields (`minReplicas`, `maxReplicas`, `autoScaling`) must be provided
 * together — the backend rejects partial updates with HTTP 400.
 *
 * @param {string} project - The project (1:1 with namespace).
 * @param {string} id - The UUID of the inference deployment.
 * @param {UpdateScalingPolicyPayload} payload - Full scaling policy to apply.
 * @throws {APIRequestError} If the API request fails.
 */
export const updateInferenceScaling = async (
  project: string,
  id: string,
  payload: UpdateScalingPolicyPayload,
): Promise<void> => {
  const response = await fetch(`/api/projects/${project}/inference/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to update inference scaling: ${errorMessage}`,
      response.status,
    );
  }
};

/**
 * Undeploys an inference deployment.
 *
 * Backed by DELETE /v1/projects/{project}/inference/{id}. Tears down
 * associated cluster-auth groups when present.
 *
 * @param {string} project - The project (1:1 with namespace).
 * @param {string} id - The UUID of the inference deployment to undeploy.
 * @throws {APIRequestError} If the API request fails or arguments are missing.
 */
export const deleteInferenceDeployment = async (
  project: string,
  id: string,
): Promise<void> => {
  if (!project) {
    throw new APIRequestError('No project provided', 422);
  }
  if (!id) {
    throw new APIRequestError('No deployment ID provided', 422);
  }

  const response = await fetch(`/api/projects/${project}/inference/${id}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to undeploy inference deployment: ${errorMessage}`,
      response.status,
    );
  }
};

/**
 * Fetches the cluster's inference model catalog joined with project-scoped
 * deployment status.
 *
 * Composes two backend calls — GET /v1/inference/models for the cluster catalog
 * (with optional server-side `statusFilter`) and GET /v1/projects/{project}/inference
 * for that project's deployments — then groups deployments per AIMClusterModel
 * via `spec.model.name` (the AIMClusterModel resource name AIWB sets at deploy
 * time; the backend backfills it from `status.resolvedModel.name` for legacy
 * v1alpha1 deploy-by-image services so consumers can always read it directly).
 *
 * @param {string} project - The project (1:1 with namespace) to check for deployed services.
 * @param {AIMStatus[]} statuses - Optional list of model statuses to filter by (server-side).
 * @returns {Promise<ParsedAIM[]>} The parsed models with deployment status.
 */
export const getInferenceCatalog = async (
  project?: string,
  statuses?: AIMStatus[],
): Promise<ParsedAIM[]> => {
  const aims = await listAllInferenceModels(statuses);
  const services = project ? await listAllInferenceDeployments(project) : [];

  const servicesByAimRef = new Map<string, AIMService[]>();
  services.forEach((service) => {
    const key = service.spec.model?.name;
    if (!key) return;
    const existing = servicesByAimRef.get(key) ?? [];
    servicesByAimRef.set(key, [...existing, service]);
  });

  return aims.map((aim) => {
    const deployedServices = servicesByAimRef.get(aim.metadata.name);
    return aimParser(aim, deployedServices);
  });
};
