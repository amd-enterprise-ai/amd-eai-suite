// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  AIM_CANONICAL_NAME_ANNOTATION,
  AIM_MODEL_NAME_LABEL,
  AIMClusterModel,
  AIMModel,
  AIMClusterServiceTemplate,
  FINE_TUNED_LABEL,
  AIMMetric,
  AIMAutoscaling,
  UpdateScalingPolicyPayload,
  AutoscalingPolicyConfig,
  AIMServiceHistoryResponse,
} from '@/types/aims';
import { Intent, StatusBadgeVariant } from '@amdenterpriseai/types';
import {
  AIMNamespaceServiceTemplate,
  AIMService,
  AIMServiceStatus,
  AIMStatus,
  AIMDeployPayload,
  AIMWorkloadStatus,
  ParsedAIM,
  AggregatedAIM,
  AimServiceReplica,
} from '@/types/aims';
import { WorkloadStatus } from '@/types/enums/workloads';
import { WorkloadLogParams, WorkloadLogResponse } from '@/types/workloads';
import { APIRequestError, getErrorMessage } from '@amdenterpriseai/utils/app';

// Autoscaling constants
export const AIM_MAX_REPLICAS = 30;

// Metric keys for vLLM
export const SCALING_METRIC_KEYS = [
  { key: 'vllm:num_requests_running', translationKey: 'runningRequests' },
  { key: 'vllm:num_requests_waiting', translationKey: 'waitingRequests' },
] as const;

// Aggregation option keys (KEDA-supported aggregation policies for autoscaling)
export const AGGREGATION_OPTION_KEYS = [
  { key: 'avg', translationKey: 'avg' },
  { key: 'max', translationKey: 'max' },
  { key: 'min', translationKey: 'min' },
] as const;

// Target type option keys
export const TARGET_TYPE_OPTION_KEYS = [
  { key: 'Value', translationKey: 'value' },
  { key: 'AverageValue', translationKey: 'averageValue' },
] as const;

export const DEFAULT_AUTOSCALING: AutoscalingFieldValues = {
  minReplicas: 1,
  maxReplicas: 3,
  metricQuery: 'vllm:num_requests_running',
  operationOverTime: 'avg',
  targetType: 'Value',
  targetValue: 10,
};

export interface AutoscalingFieldValues {
  minReplicas: number;
  maxReplicas: number;
  metricQuery: string;
  operationOverTime: string;
  targetType: string;
  targetValue: number;
}
// We shouldn't do this manually. canonicalName.split('/')[0] is good enough.
const AI_LAB_NAMES: Record<string, string> = {
  'meta-llama': 'Meta',
  mistralai: 'Mistral AI',
  qwen: 'Alibaba Cloud',
  coherelabs: 'Cohere',
  openai: 'OpenAI',
};

/**
 * Resolves canonical name prefix to human-readable AI Lab name.
 * @param canonicalName - The canonical name (e.g., "meta-llama/Llama-3.1-8B")
 * @returns Human-readable AI Lab name (e.g., "Meta")
 */
export const resolveAILabName = (canonicalName: string): string => {
  const prefix = canonicalName.split('/')[0].toLowerCase();
  return AI_LAB_NAMES[prefix] || prefix;
};

export type AIMServiceDisplayInfo = {
  title: string; // Human-readable title (e.g., "Llama 3.1 8B Instruct")
  canonicalName: string; // Canonical name (e.g., "meta-llama/Llama-3.1-8B")
  imageVersion: string; // Image version (e.g., "1.2.3")
  name: string; // Resource name (e.g., "aim-llama-2-7b-v2")
  metric: AIMMetric;
  tags?: string[];
};

/**
 * Resolves AIMService display information by combining the service spec with ParsedAIM metadata.
 * Extracts the model title, version, and optimization metric to create a user-friendly display name.
 *
 * @param {AIMService} aimService - The AIMService to resolve display info for.
 * @param {ParsedAIM[] | undefined} parsedAIMs - Optional array of parsed AIMs to match against.
 * @returns {AIMServiceDisplayInfo} Display information with title, version, resource name, metric, and formatted display name.
 */
export const resolveAIMServiceDisplay = (
  aimService: AIMService,
  parsedAIMs?: ParsedAIM[],
): AIMServiceDisplayInfo => {
  const modelRef = aimService.status.resolvedModel?.name;
  const matchingAIM = modelRef
    ? parsedAIMs?.find((aim) => aim.model === modelRef)
    : undefined;

  const displayName =
    matchingAIM?.model ?? modelRef ?? aimService.metadata.name;
  const metric = [AIMMetric.Latency, AIMMetric.Throughput].includes(
    aimService.spec.overrides?.metric as AIMMetric,
  )
    ? (aimService.spec.overrides?.metric as AIMMetric)
    : AIMMetric.Default;

  // Fine-tuned deployments aren't in the cluster catalog; the canonical and
  // user-given name live on AIMService annotations.
  const annotationCanonical =
    aimService.metadata.annotations?.[AIM_CANONICAL_NAME_ANNOTATION];
  const annotationTitle =
    aimService.metadata.annotations?.[AIM_MODEL_NAME_LABEL];

  return {
    title: matchingAIM?.title || annotationTitle || displayName,
    canonicalName:
      matchingAIM?.canonicalName || annotationCanonical || displayName,
    imageVersion: matchingAIM?.imageVersion || '',
    name: displayName,
    metric,
    tags: matchingAIM?.tags || [],
  };
};

/**
 * Maps an AIM Service status to the catalog-level AIMWorkloadStatus
 * used by AIM cards to display deployment state badges.
 */
const mapAIMServiceStatusToAIMWorkloadStatus = (
  status: AIMServiceStatus,
): AIMWorkloadStatus => {
  switch (status) {
    case AIMServiceStatus.RUNNING:
      return AIMWorkloadStatus.DEPLOYED;
    case AIMServiceStatus.PENDING:
      return AIMWorkloadStatus.PENDING;
    case AIMServiceStatus.STARTING:
      return AIMWorkloadStatus.STARTING;
    case AIMServiceStatus.DEGRADED:
      return AIMWorkloadStatus.DEGRADED;
    case AIMServiceStatus.FAILED:
      return AIMWorkloadStatus.FAILED;
    case AIMServiceStatus.DELETED:
      return AIMWorkloadStatus.DELETED;
    default:
      return AIMWorkloadStatus.NOT_DEPLOYED;
  }
};

/**
 * Parses an Aim object to extract structured information from its metadata.
 *
 * @param {AIMClusterModel} aim - The aim object to parse.
 * @param {AIMService[] | undefined} deployedServices - Optional array of all deployed services for this AIM (multiple services may share the same model name).
 * @returns {ParsedAIM} The parsed aim data with extracted description, version, tags, and status.
 */
export const aimParser = (
  aim: AIMClusterModel | AIMModel,
  deployedServices?: AIMService[],
): ParsedAIM => {
  const imageMetadata = aim.status.imageMetadata;
  const model = imageMetadata.model;
  const oci = imageMetadata.oci;

  // Check if model has a 'preview' tag
  const isPreview = model.tags?.includes('preview') || false;

  // Fine-tuned AIMModels have no spec.image, so status.imageMetadata is empty.
  // Fall back to authoritative spec/labels so callers don't need to special-case.
  // - canonicalName: spec.modelSources[0].modelId (the base model name)
  // - title: the user-given fine-tune name from the model-name label, then metadata.name
  const baseModelId =
    'modelSources' in aim.spec
      ? aim.spec.modelSources?.[0]?.modelId
      : undefined;
  const userGivenName = aim.metadata.labels?.[AIM_MODEL_NAME_LABEL];

  const parsedAim: ParsedAIM = {
    annotations: aim.metadata.annotations,
    model: aim.metadata.name,
    imageReference: aim.spec.image,
    description: {
      short: oci?.description || '',
      full: model.descriptionFull || '',
    },
    imageVersion:
      oci?.version ||
      aim.metadata.annotations['aim.eai.amd.com/source-tag'] ||
      '',
    title: model.title || oci?.title || userGivenName || aim.metadata.name,
    tags: model.tags || [],
    canonicalName: model.canonicalName || baseModelId || '',
    status: aim.status.status,
    workloadStatuses:
      deployedServices && deployedServices.length > 0
        ? deployedServices.map((s) =>
            mapAIMServiceStatusToAIMWorkloadStatus(s.status.status),
          )
        : [AIMWorkloadStatus.NOT_DEPLOYED],
    isPreview,
    isHfTokenRequired: model.hfTokenRequired === true,
    deployedService: deployedServices?.[0],
    deployedServices,
  };

  return parsedAim;
};

/**
 * Parses an AIM object and an AIM Service History object to extract structured information from their metadata.
 *
 * @param {AIMClusterModel} aim - The aim object to parse.
 * @param {AIMServiceHistoryResponse} historicalService - Required historical entity for a previously deployed AIM Service.
 * @returns {ParsedAIM} The parsed AIM data with extracted description, version, tags, and status.
 */
export const historicalAimParser = (
  aim: AIMClusterModel | AIMModel,
  historicalService: AIMServiceHistoryResponse,
): ParsedAIM => {
  const imageMetadata = aim.status.imageMetadata;
  const model = imageMetadata.model;
  const oci = imageMetadata.oci;

  // Check if model has a 'preview' tag
  const isPreview = model.tags?.includes('preview') || false;

  const historicalDeployedService: AIMService = {
    id: historicalService.id,
    metadata: {
      name: historicalService.id,
      namespace: '',
      uid: historicalService.id,
      creationTimestamp: historicalService.createdAt,
      ownerReferences: [],
      labels: {},
      annotations: {},
    },
    status: {
      status: historicalService.status,
    },
    clusterAuthGroupId: null,
    endpoints: {
      internal: '',
      external: '',
    },
    spec: {
      model: {
        name: historicalService.model,
      },
      replicas: 0,
      overrides: {},
      cacheModel: false,
      routing: {
        annotations: {},
        enabled: false,
      },
      runtimeConfigName: '',
      template: {},
    },
  };

  const parsedAim: ParsedAIM = {
    annotations: aim.metadata.annotations,
    model: aim.metadata.name,
    imageReference: aim.spec.image,
    description: {
      short: oci?.description || '',
      full: model.descriptionFull || '',
    },
    imageVersion:
      oci?.version ||
      aim.metadata.annotations['aim.eai.amd.com/source-tag'] ||
      '',
    title:
      model.title ||
      oci?.title ||
      aim.metadata.labels?.[AIM_MODEL_NAME_LABEL] ||
      aim.metadata.name,
    tags: model.tags || [],
    canonicalName:
      model.canonicalName ||
      ('modelSources' in aim.spec
        ? aim.spec.modelSources?.[0]?.modelId
        : undefined) ||
      '',
    status: aim.status.status,
    workloadStatuses: [
      mapAIMServiceStatusToAIMWorkloadStatus(historicalService.status),
    ],
    isPreview,
    isHfTokenRequired: model.hfTokenRequired === true,
    deployedService: historicalDeployedService,
    deployedServices: [historicalDeployedService],
  };

  return parsedAim;
};

/** Profile resolved from an AIMClusterServiceTemplate for a deployed service. */
export type AIMServiceProfile = {
  metric?: string | null;
  gpu?: string | null;
  /** Maps from AIMClusterServiceTemplateProfileMetadata.gpuCount. */
  templateGpuCount?: number | null;
  precision?: string | null;
};

/**
 * Fetches deployed AIM services for a namespace.
 *
 * @param {string} namespace - The namespace to fetch services from.
 * @returns {Promise<AIMService[]>} A promise that resolves to the list of deployed services.
 */
export const getAimServices = async (
  namespace: string,
): Promise<AIMService[]> => {
  const url = `/api/namespaces/${namespace}/aims/services`;

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      console.warn(
        'Failed to fetch AIM services, continuing without deployment status',
      );
      return [];
    }

    const result = await response.json();
    return result.data || [];
  } catch (error) {
    console.warn('Error fetching AIM services:', error);
    return [];
  }
};

/**
 * Fetches historical AIM services for a namespace.
 *
 * @param {string} namespace - The namespace to fetch services from.
 * @returns {Promise<AIMServiceHistoryResponse[]>} A promise that resolves to the list of historical services.
 */
export const getAimServiceHistory = async (
  namespace: string,
): Promise<AIMServiceHistoryResponse[]> => {
  const url = `/api/namespaces/${namespace}/aims/services/history`;
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch AIM service history: ${errorMessage}`,
      response.status,
    );
  }
  return (await response.json()).data || [];
};

/**
 * Fetches all available AIMs and their deployment status.
 *
 * @param {string} namespace - The namespace to check for deployed services.
 * @returns {Promise<ParsedAIM[]>} A promise that resolves to the parsed AIMs with deployment status.
 */
export const getAimClusterModels = async (
  namespace?: string,
): Promise<ParsedAIM[]> => {
  const url = `/api/cluster/aims/models`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch AIM items: ${errorMessage}`,
      response.status,
    );
  }
  const aims: { data: AIMClusterModel[] } = await response.json();

  // Fetch deployed services if namespace is provided
  const services = namespace ? await getAimServices(namespace) : [];

  const servicesByAimRef = new Map<string, AIMService[]>();
  services.forEach((service) => {
    const key = service.status.resolvedModel?.name;
    if (!key) return;
    const existing = servicesByAimRef.get(key) ?? [];
    servicesByAimRef.set(key, [...existing, service]);
  });

  return (
    aims.data?.map((aim) => {
      const deployedServices = servicesByAimRef.get(aim.metadata.name);
      return aimParser(aim, deployedServices);
    }) ?? []
  );
};

export const getAimService = async (
  namespace: string,
  id: string,
): Promise<AIMService> => {
  const url = `/api/namespaces/${namespace}/aims/services/${id}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch AIM service: ${errorMessage}`,
      response.status,
    );
  }

  const service = await response.json();
  return service;
};

export const getAimServiceReplicas = async (
  namespace: string,
  id: string,
): Promise<AimServiceReplica[]> => {
  const url = `/api/namespaces/${namespace}/aims/services/${id}/replicas`;
  const response = await fetch(url);
  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch AIM service replicas: ${errorMessage}`,
      response.status,
    );
  }
  return (await response.json()).data ?? [];
};

/**
 * Fetches logs for an AIM service.
 *
 * @param {string} namespace - The namespace containing the service.
 * @param {string} serviceId - The service ID (UUID) to fetch logs for.
 * @param {WorkloadLogParams} params - Optional parameters for filtering logs.
 * @returns {Promise<WorkloadLogResponse>} A promise that resolves to the logs response.
 * @throws {APIRequestError} If the API request fails.
 */
export const getAimServiceLogs = async (
  namespace: string,
  serviceId: string,
  params: WorkloadLogParams = {},
): Promise<WorkloadLogResponse> => {
  const urlParams = new URLSearchParams();

  // AIM logs endpoint requires 'start' and 'end' parameters (ISO format)
  // Default to last 24 hours if not provided
  const end = params.endDate ? new Date(params.endDate) : new Date();
  const start = params.startDate
    ? new Date(params.startDate)
    : new Date(end.getTime() - 24 * 60 * 60 * 1000);

  urlParams.append('start', start.toISOString());
  urlParams.append('end', end.toISOString());

  if (params.pageToken) {
    // Ensure the pageToken has timezone info
    let pageToken = params.pageToken;
    // If it doesn't end with 'Z' or contain timezone offset (+/-), assume UTC and add 'Z'
    if (!pageToken.endsWith('Z') && !/[+-]\d{2}:\d{2}$/.test(pageToken)) {
      pageToken = pageToken + 'Z';
    }
    urlParams.append('pageToken', pageToken);
  }
  if (params.level) urlParams.append('level', params.level);
  if (params.limit) urlParams.append('limit', params.limit.toString());
  if (params.direction) urlParams.append('direction', params.direction);
  if (params.logType) urlParams.append('logType', params.logType);

  const response = await fetch(
    `/api/namespaces/${namespace}/aims/services/${serviceId}/logs?${urlParams.toString()}`,
    { method: 'GET' },
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to get AIM service logs: ${errorMessage}`,
      response.status,
    );
  }

  return response.json();
};

export const getAimClusterModel = async (
  resourceName: string,
): Promise<AIMClusterModel> => {
  if (!resourceName) {
    throw new APIRequestError('No AIM resource name provided', 422);
  }

  const response = await fetch(`/api/cluster/aims/models/${resourceName}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch AIM items: ${errorMessage}`,
      response.status,
    );
  }

  const aim = await response.json();
  return aim;
};

export const getAimNamespaceModel = async (
  resourceName: string,
  namespace: string,
): Promise<AIMModel> => {
  if (!resourceName) {
    throw new APIRequestError('No AIM model resource name provided', 422);
  }

  const response = await fetch(
    `/api/namespaces/${namespace}/aims/models/${encodeURIComponent(resourceName)}`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    },
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch AIM model: ${errorMessage}`,
      response.status,
    );
  }

  return await response.json();
};

/**
 * Fetches service templates for a specific AIM.
 * Service templates contain optimization profiles (latency/throughput) with GPU requirements.
 *
 * @param {string} aimResourceName - The AIM resource name to get templates for.
 * @returns {Promise<AIMClusterServiceTemplate[]>} A promise that resolves to the list of service templates.
 * @throws {APIRequestError} If the API request fails.
 */
export const getAimClusterServiceTemplates = async (
  aimResourceName: string,
): Promise<AIMClusterServiceTemplate[]> => {
  if (!aimResourceName) {
    throw new APIRequestError('No AIM resource name provided', 422);
  }

  const url = `/api/cluster/aims/templates?aimResourceName=${encodeURIComponent(aimResourceName)}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch AIM service templates: ${errorMessage}`,
      response.status,
    );
  }

  const result = await response.json();
  return result.data || [];
};

/**
 * Resolves hardware profile metadata for each AIM service by looking up its
 * selected template via the appropriate template API.
 *
 * For cluster-scoped models: uses GET /cluster/aims/templates.
 * For namespace-scoped fine-tuned models (label aiwb.apps.eai.amd.com/fine-tuned=true):
 * uses GET /namespaces/{namespace}/models/{model}/templates.
 *
 * Groups services by model name to avoid redundant template fetches, then
 * matches each service's resolvedTemplate.name to a template's metadata.name.
 *
 * @param services - Deployed AIM services to resolve profiles for.
 * @returns Map from service ID to its resolved profile.
 */
export const fetchProfilesForServices = async (
  services: AIMService[],
): Promise<Map<string, AIMServiceProfile>> => {
  // Track unique models with their fetch context (finetuned status + namespace).
  const modelNameToServiceIds = new Map<string, string[]>();
  const modelNameToContext = new Map<
    string,
    { isFinetuned: boolean; namespace: string }
  >();

  for (const service of services) {
    const modelName = service.status.resolvedModel?.name;
    if (!modelName || !service.id) continue;
    if (!modelNameToServiceIds.has(modelName)) {
      modelNameToServiceIds.set(modelName, []);
      modelNameToContext.set(modelName, {
        isFinetuned: service.metadata.labels[FINE_TUNED_LABEL] === 'true',
        namespace: service.metadata.namespace,
      });
    }
    modelNameToServiceIds.get(modelName)!.push(String(service.id));
  }

  const templatesByModel = new Map<string, AIMClusterServiceTemplate[]>();
  await Promise.all(
    Array.from(modelNameToServiceIds.keys()).map(async (modelName) => {
      const context = modelNameToContext.get(modelName)!;
      try {
        const templates = context.isFinetuned
          ? await getAimNamespaceServiceTemplates(context.namespace, modelName)
          : await getAimClusterServiceTemplates(modelName);
        templatesByModel.set(
          modelName,
          templates as AIMClusterServiceTemplate[],
        );
      } catch (error) {
        console.warn(
          `Failed to fetch templates for model "${modelName}":`,
          error,
        );
        templatesByModel.set(modelName, []);
      }
    }),
  );

  const profileMap = new Map<string, AIMServiceProfile>();
  for (const service of services) {
    const modelName = service.status.resolvedModel?.name;
    const templateName = service.status.resolvedTemplate?.name;
    if (!service.id || !modelName || !templateName) continue;
    const templates = templatesByModel.get(modelName) ?? [];
    const template = templates.find((t) => t.metadata.name === templateName);
    if (!template?.status.profile?.metadata) continue;
    const meta = template.status.profile.metadata;
    profileMap.set(String(service.id), {
      metric: meta.metric ?? null,
      gpu: meta.gpu ?? null,
      templateGpuCount: meta.gpuCount ?? null,
      precision: meta.precision ?? null,
    });
  }
  return profileMap;
};

/**
 * Deploys an AIM by creating an AIMService.
 *
 * @param {string} namespace - The namespace (project) to deploy to.
 * @param {AIMDeployPayload} payload - The deployment configuration.
 * @returns {Promise<AIMService>} A promise that resolves to the deployment result.
 * @throws {APIRequestError} If the API request fails.
 */
export const deployAim = async (
  namespace: string,
  payload: AIMDeployPayload,
): Promise<AIMService> => {
  if (!namespace) {
    throw new APIRequestError('No namespace selected', 422);
  }

  const response = await fetch(`/api/namespaces/${namespace}/aims/services`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to deploy AIM: ${errorMessage}`,
      response.status,
    );
  }

  return response.json();
};

/**
 * Undeploys an AIM service by deleting it.
 *
 * @param {string} namespace - The namespace containing the service.
 * @param {string} serviceId - The service ID (UUID) to undeploy.
 * @returns {Promise<void>} A promise that resolves when the service is deleted.
 * @throws {APIRequestError} If the API request fails.
 */
export const undeployAim = async (
  namespace: string,
  serviceId: string,
): Promise<void> => {
  if (!namespace) {
    throw new APIRequestError('No namespace provided', 422);
  }

  if (!serviceId) {
    throw new APIRequestError('No service ID provided', 422);
  }

  const response = await fetch(
    `/api/namespaces/${namespace}/aims/services/${serviceId}`,
    {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    },
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to undeploy AIM service: ${errorMessage}`,
      response.status,
    );
  }
};

/**
 * Updates the autoscaling policy for an AIM service.
 *
 * Configures min/max replicas, scaling metric, aggregation operation,
 * target type, and target value for horizontal pod autoscaling.
 *
 * @param {string} namespace - The namespace (project) where the AIM service is deployed.
 * @param {string} id - The unique identifier of the AIM service to update.
 * @param {UpdateScalingPolicyPayload} payload - The scaling policy configuration.
 * @returns {Promise<void>} A promise that resolves when the update is successful.
 * @throws {APIRequestError} If the API request fails.
 */
export const updateAimScalingPolicy = async (
  namespace: string,
  id: string,
  payload: UpdateScalingPolicyPayload,
): Promise<void> => {
  const response = await fetch(
    `/api/namespaces/${namespace}/aims/services/${id}`,
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    },
  );

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to update AIM service scaling: ${errorMessage}`,
      response.status,
    );
  }
};

/**
 * Fetches namespace-scoped AIMServiceTemplate CRs for a fine-tuned AIMModel.
 *
 * Calls GET /namespaces/{namespace}/models/{modelId}/templates.
 * Returns the full CRD structure; callers are responsible for reading
 * the fields they need from metadata and spec.
 *
 * @param {string} namespace - The namespace (project) the AIMModel lives in.
 * @param {string} modelId - The AIMModel CR name (resource name).
 * @returns {Promise<AIMNamespaceServiceTemplate[]>} List of available deployment templates.
 * @throws {APIRequestError} If the API request fails.
 */
export const getAimNamespaceServiceTemplates = async (
  namespace: string,
  modelId: string,
): Promise<AIMNamespaceServiceTemplate[]> => {
  if (!namespace) {
    throw new APIRequestError('No namespace selected', 422);
  }
  if (!modelId) {
    throw new APIRequestError('No model ID provided', 422);
  }

  const url = `/api/namespaces/${namespace}/models/${modelId}/templates`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorMessage = await getErrorMessage(response);
    throw new APIRequestError(
      `Failed to fetch AIM service templates: ${errorMessage}`,
      response.status,
    );
  }

  const result = await response.json();
  return result.data || [];
};

/**
 * Generates a Kubernetes HPA policy using OpenTelemetry metrics from vLLM.
 *
 * @param {Partial<AIMAutoscaling>} config - Autoscaling configuration parameters
 * @param {string} [config.metricQuery] - OpenTelemetry metric query to monitor (default: 'vllm:num_requests_running')
 * @param {string} [config.operationOverTime] - Aggregation operation for metric values (default: 'avg')
 * @param {string} [config.targetType] - Target type for scaling ('Value', 'AverageValue', or 'Utilization', default: 'Value')
 * @param {number} [config.targetValue] - Target metric value that triggers scaling (default: 10)
 * @returns {AutoscalingPolicyConfig} Kubernetes autoscaling policy configuration
 *
 * @see {@link https://github.com/silogen/aim-engine/blob/main/docs/docs/guides/scaling-and-autoscaling.md}
 */
export const createAimScalingPolicyConfig = ({
  metricQuery = DEFAULT_AUTOSCALING.metricQuery,
  operationOverTime = DEFAULT_AUTOSCALING.operationOverTime,
  targetType = DEFAULT_AUTOSCALING.targetType,
  targetValue = DEFAULT_AUTOSCALING.targetValue,
}: Partial<AIMAutoscaling> = {}): AutoscalingPolicyConfig => {
  // Keys MUST match CRD-native format exactly because the backend passes
  // this dict through as-is to Kubernetes (dict[str, Any]):
  // - "podmetric" (all lowercase, NOT camelCase — CRD spec)
  // - "metricNames", "operationOverTime" (standard camelCase — CRD spec)
  // - target.value must be string (Go struct expects string, not number)
  return {
    metrics: [
      {
        type: 'PodMetric',
        podmetric: {
          metric: {
            backend: 'opentelemetry',
            metricNames: [
              'vllm:num_requests_running',
              'vllm:num_requests_waiting',
            ],
            query: metricQuery,
            operationOverTime: operationOverTime,
          },
          target: {
            type: targetType,
            value: String(targetValue),
          },
        },
      },
    ],
  };
};

/**
 * Returns status badge variants for AIM service statuses with localized labels.
 * Maps each AIMServiceStatus to its corresponding display properties (label, intent, color, icon).
 *
 * @param t - Translation function to localize status labels
 * @returns A mapping of AIMServiceStatus values to their display variants
 */
export const getAIMServiceStatusVariants = (
  t: (key: string) => string,
): Record<AIMServiceStatus, StatusBadgeVariant> => ({
  [AIMServiceStatus.PENDING]: {
    label: t('models:status.pending'),
    intent: Intent.PENDING,
  },
  [AIMServiceStatus.DEGRADED]: {
    label: t('models:status.degraded'),
    intent: Intent.WARNING,
  },
  [AIMServiceStatus.RUNNING]: {
    label: t('models:status.running'),
    intent: Intent.SUCCESS,
  },
  [AIMServiceStatus.FAILED]: {
    label: t('models:status.failed'),
    intent: Intent.DANGER,
  },
  [AIMServiceStatus.STARTING]: {
    label: t('models:status.starting'),
    intent: Intent.PENDING,
  },
  [AIMServiceStatus.DELETED]: {
    label: t('models:status.deleted'),
    intent: Intent.DANGER,
  },
});

/**
 * Converts an AIM Service status to a Workload status for aggregation and display purposes.
 *
 * @param {AIMServiceStatus} status - The AIM service status to convert.
 * @returns {WorkloadStatus} The corresponding workload status.
 */
export const mapAIMServiceStatusToWorkloadStatus = (
  status: AIMServiceStatus,
): WorkloadStatus => {
  switch (status) {
    case AIMServiceStatus.PENDING:
      return WorkloadStatus.PENDING;
    case AIMServiceStatus.STARTING:
      return WorkloadStatus.STARTING;
    case AIMServiceStatus.RUNNING:
      return WorkloadStatus.RUNNING;
    case AIMServiceStatus.DEGRADED:
      return WorkloadStatus.DEGRADED;
    case AIMServiceStatus.FAILED:
      return WorkloadStatus.FAILED;
    default:
      return WorkloadStatus.UNKNOWN;
  }
};

/**
 * Transforms aggregated AIMs into an array of AggregatedAIM objects.
 * Sorts versions by image version (descending) and computes aggregated properties.
 *
 * @param {ParsedAIM[] | undefined} aims - Optional array of parsed AIMs to aggregate.
 * @returns {AggregatedAIM[]} An array of aggregated AIMs.
 */
export const transformToAggregatedAIMs = (
  aims?: ParsedAIM[],
): AggregatedAIM[] => {
  if (!aims) {
    return [];
  }

  const aggregated = aims.reduce(
    (result, aim) => {
      // Use the repository as the key to aggregate the AIMs
      const key = aim.annotations['aim.eai.amd.com/source-repository'];

      if (!result[key]) {
        result[key] = [];
      }

      result[key].push(aim);

      return result;
    },
    {} as Record<string, ParsedAIM[]>,
  );

  // Convert `major.minor.patch` to a sortable number; ignore suffixes like `-preview-3` or `+build.1`.
  const versionStringToNumber = (v: string) => {
    const m = v.match(/(\d+)\.(\d+)\.(\d+)/);
    if (!m) return 0;
    return Number(`${m[1]}${m[2].padStart(3, '0')}${m[3].padStart(3, '0')}`);
  };

  // Match official versions like `1.2.3` or `v1.2.3`, and allow optional `+build` metadata.
  // Any prerelease suffix (for example `-preview`, `-beta`, `-rc`) is excluded.
  const officialReleaseRegex = /^v?\d+\.\d+\.\d+(\+[0-9A-Za-z.-]+)?$/;

  const result = Object.entries(aggregated).map(([repository, aims]) => {
    // Sort aims by imageVersion in descending order (latest first)
    const sortedAims = [...aims].sort((a, b) => {
      return (
        versionStringToNumber(b.imageVersion) -
        versionStringToNumber(a.imageVersion)
      );
    });

    const latestAim =
      sortedAims.find(
        (aim) =>
          officialReleaseRegex.test(aim.imageVersion.trim()) &&
          aim.status === AIMStatus.READY,
      ) ?? null;

    const metaSource = latestAim ?? sortedAims[0];
    const { title, canonicalName, imageVersion, description, tags } =
      metaSource;

    let isHfTokenRequired = false;
    let isSupported = false;
    const deploymentCounts: Record<AIMWorkloadStatus, number> = {
      [AIMWorkloadStatus.DEPLOYED]: 0,
      [AIMWorkloadStatus.DEGRADED]: 0,
      [AIMWorkloadStatus.PENDING]: 0,
      [AIMWorkloadStatus.STARTING]: 0,
      [AIMWorkloadStatus.FAILED]: 0,
      [AIMWorkloadStatus.NOT_DEPLOYED]: 0,
      [AIMWorkloadStatus.DELETED]: 0,
    };

    sortedAims.forEach((aim) => {
      // Counting the number of deployments for each status.
      aim.workloadStatuses.forEach((status) => {
        deploymentCounts[status]++;
      });

      aim.isLatest =
        latestAim !== null && aim.imageVersion === latestAim.imageVersion;

      // Check whether it requires hf token
      isHfTokenRequired = isHfTokenRequired || aim.isHfTokenRequired;

      // At least one version with Ready status makes the model supported
      isSupported = isSupported || aim.status === AIMStatus.READY;
    });

    return {
      repository,
      parsedAIMs: sortedAims,
      latestAim,
      isSupported,
      deploymentCounts,
      aggregated: {
        title,
        aiLabName: resolveAILabName(canonicalName),
        canonicalName,
        latestImageVersion: imageVersion,
        isHfTokenRequired,
        tags,
        description: {
          short: description.short,
          full: description.full,
        },
      },
    };
  });

  // Supported models appear first, unsupported last
  result.sort((a, b) => Number(b.isSupported) - Number(a.isSupported));
  return result;
};
