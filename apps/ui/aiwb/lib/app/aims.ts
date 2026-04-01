// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  AIMClusterModel,
  AIMClusterServiceTemplate,
  AIMMetric,
  AIMService,
  AIMServiceStatus,
  AIMStatus,
  AIMDeployPayload,
  AIMWorkloadStatus,
  ParsedAIM,
  AIMAutoscaling,
  UpdateScalingPolicyPayload,
  AutoscalingPolicyConfig,
  AggregatedAIM,
  AIMServiceHistoryResponse,
} from '@/types/aims';
import {
  Intent,
  StatusBadgeVariant,
  WorkloadLogParams,
  WorkloadLogResponse,
  WorkloadStatus,
} from '@amdenterpriseai/types';
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
  resourceName: string; // Resource name (e.g., "aim-llama-2-7b-v2")
  metric: AIMMetric;
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
    ? parsedAIMs?.find((aim) => aim.resourceName === modelRef)
    : undefined;

  const displayName =
    matchingAIM?.resourceName ?? modelRef ?? aimService.metadata.name;
  const metric = [AIMMetric.Latency, AIMMetric.Throughput].includes(
    aimService.spec.overrides?.metric as AIMMetric,
  )
    ? (aimService.spec.overrides?.metric as AIMMetric)
    : AIMMetric.Default;

  return {
    title: matchingAIM?.title || displayName,
    canonicalName: matchingAIM?.canonicalName || displayName,
    imageVersion: matchingAIM?.imageVersion || '',
    resourceName: displayName,
    metric,
  };
};

/**
 * Parses an Aim object to extract structured information from its metadata.
 *
 * @param {AIMClusterModel} aim - The aim object to parse.
 * @param {AIMService[] | undefined} deployedServices - Optional array of all deployed services for this AIM (multiple services may share the same model name).
 * @returns {ParsedAIM} The parsed aim data with extracted description, version, tags, and status.
 */
export const aimParser = (
  aim: AIMClusterModel,
  deployedServices?: AIMService[],
): ParsedAIM => {
  const imageMetadata = aim.status.imageMetadata;
  const model = imageMetadata.model;
  const originalLabels = imageMetadata.originalLabels;

  // Check if model has a 'preview' tag
  const isPreview = model.tags?.includes('preview') || false;

  // Determine workload status based on deployed service
  const _getWorkloadStatus = (_deployedService?: AIMService) => {
    let workloadStatus = AIMWorkloadStatus.NOT_DEPLOYED;
    if (_deployedService) {
      const serviceStatus = _deployedService.status.status;
      if (serviceStatus === AIMServiceStatus.RUNNING) {
        workloadStatus = AIMWorkloadStatus.DEPLOYED;
      } else if (
        serviceStatus === AIMServiceStatus.PENDING ||
        serviceStatus === AIMServiceStatus.STARTING
      ) {
        workloadStatus = AIMWorkloadStatus.PENDING;
      } else if (serviceStatus === AIMServiceStatus.DEGRADED) {
        workloadStatus = AIMWorkloadStatus.DEGRADED;
      } else if (serviceStatus === AIMServiceStatus.FAILED) {
        workloadStatus = AIMWorkloadStatus.FAILED;
      }
    }

    return workloadStatus;
  };

  const parsedAim: ParsedAIM = {
    anotations: aim.metadata.annotations,
    resourceName: aim.resourceName,
    model: aim.metadata.name,
    imageReference: aim.spec.image,
    description: {
      short: originalLabels.orgOpencontainersImageDescription || '',
      full: originalLabels.comAmdAimDescriptionFull || '',
    },
    imageVersion:
      originalLabels.orgOpencontainersImageVersion ||
      aim.metadata.annotations.aimEaiAmdComSourceTag ||
      '',
    title: model.title || originalLabels.comAmdAimTitle || '',
    tags: model.tags || [],
    canonicalName: model.canonicalName || '',
    status: aim.status.status,
    workloadStatuses:
      deployedServices && deployedServices.length > 0
        ? deployedServices.map(_getWorkloadStatus)
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
  aim: AIMClusterModel,
  historicalService: AIMServiceHistoryResponse,
): ParsedAIM => {
  const imageMetadata = aim.status.imageMetadata;
  const model = imageMetadata.model;
  const originalLabels = imageMetadata.originalLabels;

  // Check if model has a 'preview' tag
  const isPreview = model.tags?.includes('preview') || false;

  const _getWorkloadStatus = (serviceStatus: AIMServiceStatus) => {
    let workloadStatus = AIMWorkloadStatus.NOT_DEPLOYED;
    if (serviceStatus) {
      if (serviceStatus === AIMServiceStatus.RUNNING) {
        workloadStatus = AIMWorkloadStatus.DEPLOYED;
      } else if (
        serviceStatus === AIMServiceStatus.PENDING ||
        serviceStatus === AIMServiceStatus.STARTING
      ) {
        workloadStatus = AIMWorkloadStatus.PENDING;
      } else if (serviceStatus === AIMServiceStatus.DEGRADED) {
        workloadStatus = AIMWorkloadStatus.DEGRADED;
      } else if (serviceStatus === AIMServiceStatus.FAILED) {
        workloadStatus = AIMWorkloadStatus.FAILED;
      } else if (serviceStatus === AIMServiceStatus.DELETED) {
        workloadStatus = AIMWorkloadStatus.DELETED;
      }
    }

    return workloadStatus;
  };

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
    resourceName: historicalService.id,
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
    anotations: aim.metadata.annotations,
    resourceName: aim.resourceName,
    model: aim.metadata.name,
    imageReference: aim.spec.image,
    description: {
      short: originalLabels.orgOpencontainersImageDescription || '',
      full: originalLabels.comAmdAimDescriptionFull || '',
    },
    imageVersion:
      originalLabels.orgOpencontainersImageVersion ||
      aim.metadata.annotations.aimEaiAmdComSourceTag ||
      '',
    title: model.title || originalLabels.comAmdAimTitle || '',
    tags: model.tags || [],
    canonicalName: model.canonicalName || '',
    status: aim.status.status,
    workloadStatuses: [_getWorkloadStatus(historicalService.status)],
    isPreview,
    isHfTokenRequired: model.hfTokenRequired === true,
    deployedService: historicalDeployedService,
    deployedServices: [historicalDeployedService],
  };

  return parsedAim;
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
      // If services can't be fetched, log but don't fail
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

  // Parse AIMs and match with deployed services by resourceName
  return (
    aims.data?.map((aim) => {
      const deployedServices = servicesByAimRef.get(aim.resourceName);
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
    urlParams.append('page_token', pageToken);
  }
  if (params.level) urlParams.append('level', params.level);
  if (params.limit) urlParams.append('limit', params.limit.toString());
  if (params.direction) urlParams.append('direction', params.direction);
  if (params.logType) urlParams.append('log_type', params.logType);

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

export const getAimByResourceName = async (
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

/**
 * Fetches service templates for a specific AIM.
 * Service templates contain optimization profiles (latency/throughput) with GPU requirements.
 *
 * @param {string} aimResourceName - The AIM resource name to get templates for.
 * @returns {Promise<AIMClusterServiceTemplate[]>} A promise that resolves to the list of service templates.
 * @throws {APIRequestError} If the API request fails.
 */
export const getAimServiceTemplates = async (
  aimResourceName: string,
): Promise<AIMClusterServiceTemplate[]> => {
  if (!aimResourceName) {
    throw new APIRequestError('No AIM resource name provided', 422);
  }

  const url = `/api/cluster/aims/templates?aim_resource_name=${encodeURIComponent(aimResourceName)}`;

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
 * Deploys an AIM by creating an AIMService.
 *
 * @param {string} namespace - The namespace (project) to deploy to.
 * @param {AIMDeployPayload} payload - The deployment configuration.
 * @returns {Promise<unknown>} A promise that resolves to the deployment result.
 * @throws {APIRequestError} If the API request fails.
 */
export const deployAim = async (
  namespace: string,
  payload: AIMDeployPayload,
): Promise<unknown> => {
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
    label: t(`status.${AIMServiceStatus.PENDING}`),
    intent: Intent.PENDING,
  },
  [AIMServiceStatus.DEGRADED]: {
    label: t(`status.${AIMServiceStatus.DEGRADED}`),
    intent: Intent.WARNING,
  },
  [AIMServiceStatus.RUNNING]: {
    label: t(`status.${AIMServiceStatus.RUNNING}`),
    intent: Intent.SUCCESS,
  },
  [AIMServiceStatus.FAILED]: {
    label: t(`status.${AIMServiceStatus.FAILED}`),
    intent: Intent.DANGER,
  },
  [AIMServiceStatus.STARTING]: {
    label: t(`status.${AIMServiceStatus.STARTING}`),
    intent: Intent.PENDING,
  },
  [AIMServiceStatus.DELETED]: {
    label: t(`status.${AIMServiceStatus.DELETED}`),
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
    case AIMServiceStatus.STARTING:
      return WorkloadStatus.PENDING;
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
      const key = aim.anotations.aimEaiAmdComSourceRepository;

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
