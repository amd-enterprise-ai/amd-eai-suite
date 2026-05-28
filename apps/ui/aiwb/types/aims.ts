// Copyright © Advanced Micro Devices, Inc., or its affiliates.

// SPDX-License-Identifier: MIT

/** Label set on AIMService resources backed by a namespace-scoped fine-tuned AIMModel. */
export const FINE_TUNED_LABEL = 'aiwb.apps.eai.amd.com/fine-tuned';

/** Labels stamped on AIMModel CRs by the finetuning pipeline. */
export const AIM_MODEL_NAME_LABEL = 'aiwb.apps.eai.amd.com/model-name';
export const AIM_MODEL_WORKLOAD_ID_LABEL = 'airm.silogen.ai/workload-id';

/**
 * Annotation on fine-tuned AIMService CRs carrying the slash-preserved canonical
 * (base model) name — e.g. `meta-llama/Llama-3.2-1B-Instruct`. Annotation rather
 * than label because K8s labels can't contain `/`. Used by the connect modal to
 * render copy-paste-able code samples that match what vLLM is actually serving as.
 */
export const AIM_CANONICAL_NAME_ANNOTATION =
  'aiwb.apps.eai.amd.com/canonical-name';

/**
 * AimWorkloadStatus: Frontend-friendly deployment status for UI display
 *
 * Purpose: Simplified, high-level status used in the frontend for displaying
 * the deployment state of an AIM in the catalog UI.
 *
 * This status is derived from AIMServiceStatus by mapping Kubernetes states
 * to user-friendly values.
 */
export enum AIMWorkloadStatus {
  DEPLOYED = 'deployed',
  DEGRADED = 'degraded',
  NOT_DEPLOYED = 'not_deployed',
  PENDING = 'pending',
  STARTING = 'starting',
  FAILED = 'failed',
  DELETED = 'deleted',
}

/**
 * AIMStatus: Catalog status of the AIM model/image itself
 *
 * Purpose: Represents the availability and readiness of the AIM model
 * in the cluster catalog (not the deployment status).
 *
 * Values come from the Kubernetes AIMClusterModel CRD status field.
 *
 * This is about the model's availability, not whether it's deployed.
 */
export enum AIMStatus {
  NOT_AVAILABLE = 'NotAvailable',
  PENDING = 'Pending',
  PROGRESSING = 'Progressing',
  READY = 'Ready',
  DEGRADED = 'Degraded',
  FAILED = 'Failed',
  DELETED = 'Deleted',
}

/**
 * AIMServiceStatus: Runtime status of a deployed AIM service instance
 *
 * Purpose: Represents the current state of a running AIM deployment
 * (the AIMService Kubernetes resource).
 *
 * This is about the deployment's runtime state, not the model availability.
 * doc: https://github.com/silogen/aim-engine/blob/main/docs/docs/concepts/services.md
 */
export enum AIMServiceStatus {
  PENDING = 'Pending',
  STARTING = 'Starting',
  RUNNING = 'Running',
  DEGRADED = 'Degraded',
  FAILED = 'Failed',
  DELETED = 'Deleted',
}

export type AIMClusterModelMetadataAnnotations = {
  'aim.eai.amd.com/source-registry': string; // e.g. docker.io
  'aim.eai.amd.com/source-repository': string; // e.g. amdenterpriseai/aim-mistralai-mixtral-8x7b-instruct-v0-1
  'aim.eai.amd.com/source-tag': string; // e.g. 0.8.4
};

/**
 * Complete AIM resource as returned by the API
 */
export type AIMClusterModel = {
  metadata: {
    name: string;
    namespace: string | null;
    uid: string;
    labels: Record<string, string>;
    annotations: AIMClusterModelMetadataAnnotations;
    creationTimestamp: string;
    ownerReferences: {
      apiVersion: string;
      blockOwnerDeletion: boolean;
      kind: string;
      name: string;
      uid: string;
    }[];
  };
  spec: {
    image: string;
  };
  status: {
    status: AIMStatus;
    imageMetadata: AIMImageMetadata;
  };
};

/** Namespace-scoped AIMModel as returned by GET /namespaces/{ns}/aims/models/{id} */
export type AIMModel = {
  metadata: {
    name: string;
    namespace: string | null;
    uid: string;
    labels: Record<string, string>;
    annotations: Record<string, string>;
    creationTimestamp: string;
    ownerReferences: {
      apiVersion: string;
      blockOwnerDeletion: boolean;
      kind: string;
      name: string;
      uid: string;
    }[];
  };
  spec: {
    image: string;
    modelSources: { modelId: string; sourceUri: string }[];
  };
  status: {
    status: string;
    conditions: AIMServiceCondition[];
    imageMetadata: AIMImageMetadata;
  };
};

export type AIMServiceRuntime = {
  currentReplicas?: number | null;
  desiredReplicas?: number | null;
  minReplicas?: number | null;
  maxReplicas?: number | null;
  replicas?: string | null;
};

export type AIMServiceCondition = {
  lastTransitionTime: string;
  message: string;
  observedGeneration: number;
  reason: string;
  status: string;
  type: string;
};

export type AIMServiceMetric = {
  type: string; // 'PodMetric'
  podmetric: {
    metric: {
      backend: string;
      metricNames: string[];
      query: string;
      operationOverTime: string;
    };
    target: {
      type: string; // 'Value' | 'AverageValue' | 'Utilization'
      value: string;
    };
  };
};

/**
 * AIMService spec from Kubernetes
 * Contains model configuration and autoscaling settings
 */
export type AIMServiceSpec = {
  model: {
    name?: string;
    image?: string;
  };
  replicas: number;
  overrides: Record<string, unknown>;
  cacheModel: boolean;
  routing?: {
    annotations: Record<string, string>;
    enabled: boolean;
  };
  runtimeConfigName: string;
  template: Record<string, unknown>;
  minReplicas?: number;
  maxReplicas?: number;
  autoScaling?: {
    metrics: AIMServiceMetric[];
  };
};

/**
 * AIMService represents a deployed AIM instance
 */
export type AIMService = {
  id: string | null;
  metadata: {
    name: string;
    namespace: string;
    uid: string;
    labels: Record<string, string>;
    annotations: Record<string, string>;
    creationTimestamp: string;
    ownerReferences: unknown[];
  };
  spec: AIMServiceSpec;
  status: {
    status: AIMServiceStatus;
    routing?: {
      path: string;
    };
    conditions?: AIMServiceCondition[];
    observedGeneration?: number;
    runtime?: AIMServiceRuntime;
    resolvedModel?: { name?: string };
    resolvedTemplate?: { name?: string };
  };
  clusterAuthGroupId: string | null;
  endpoints: {
    internal: string;
    external?: string;
  };
};

export type AIMServiceHistoryResponse = {
  id: string;
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  updatedBy: string;
  model: string;
  status: AIMServiceStatus;
  metric: AIMMetric;
};

export type ParsedAIM = {
  model: string;
  imageReference: string;
  annotations: Record<string, string>;
  description: {
    short: string;
    full: string;
  };
  title: string;
  imageVersion: string;
  canonicalName: string;
  tags: string[];
  status: AIMStatus | string;
  workloadStatuses: AIMWorkloadStatus[];
  isPreview: boolean;
  isHfTokenRequired: boolean;
  isLatest?: boolean;
  // Deployment information
  /**
   * @deprecated Use deployedServices instead
   */
  deployedService?: AIMService;
  // Deployment information as one model can be deployed multiple times
  deployedServices?: AIMService[];
};

/**
 * AggregatedAIM represents a model family with multiple versions
 * grouped by their source repository.
 */
export type AggregatedAIM = {
  repository: string;
  parsedAIMs: ParsedAIM[];
  /**
   * Latest official release that is READY, or null when none available.
   * Best default for deployment when non-null.
   */
  latestAim: ParsedAIM | null;
  /**
   * True if at least one version has AIMStatus.READY.
   */
  isSupported: boolean;
  /**
   * Counts of deployments for each status.
   */
  deploymentCounts: Record<AIMWorkloadStatus, number>;
  aggregated: {
    title: string;
    aiLabName: string;
    canonicalName: string;
    latestImageVersion: string;
    isHfTokenRequired: boolean;
    tags: string[];
    description: {
      short: string;
      full: string;
    };
  };
};

export type AIMAutoscaling = {
  metricQuery: string;
  operationOverTime: string;
  targetType: string;
  targetValue: number;
};

export type AIMDeployPayload = {
  model: string;
  replicas?: number;
  imagePullSecrets?: string[];
  hfToken?: string;
  metric?: string;
  allowUnoptimized?: boolean;

  // Autoscaling configuration
  minReplicas?: number;
  maxReplicas?: number;
  autoScaling?: AutoscalingPolicyConfig;

  // AIMServiceOverrides / template selection (advanced profile params)
  precision?: string;
  gpuModel?: string;
  gpuCount?: number;
  templateName?: string;
};

export type UpdateScalingPolicyPayload = {
  minReplicas: number;
  maxReplicas: number;
  autoScaling: AutoscalingPolicyConfig;
};

/**
 * Autoscaling policy payload structure sent to the Kubernetes API.
 *
 * IMPORTANT: Keys must match the CRD-native format exactly because the backend
 * passes this dict through as-is to Kubernetes (dict[str, Any]).
 * - `podmetric` (all lowercase, NOT camelCase)
 * - `metricNames`, `operationOverTime` (standard camelCase)
 * - `target.value` must be string (Go CRD struct expects string)
 */
export type AutoscalingPolicyConfig = {
  metrics: Array<{
    type: 'PodMetric';
    podmetric: {
      metric: {
        backend: 'opentelemetry';
        metricNames: string[];
        query: string;
        operationOverTime: string;
      };
      target: {
        type: string;
        value: string;
      };
    };
  }>;
};

/**
 * AIMMetric: Optimization goal for an AIM deployment.
 * Default means AIM selects the most appropriate metric automatically.
 */
export enum AIMMetric {
  Latency = 'latency',
  Throughput = 'throughput',
  Default = 'default',
}

/** Runtime profile type from AIMClusterServiceTemplate discovery. Only 'optimized' is treated as optimized. */

/** Canonical `metadata.type` value from discovery (see `AIMClusterServiceTemplateProfileMetadata`). */
export const AIM_PROFILE_TYPE_OPTIMIZED = 'optimized' as const;

/** Profile metadata from AIMClusterServiceTemplate status.profile (discovery). */
export type AIMClusterServiceTemplateProfileMetadata = {
  type?: 'optimized' | 'preview' | 'unoptimized';
  engine?: string;
  gpu?: string;
  gpuCount?: number;
  metric?: string;
  precision?: string;
};

/**
 * AIMClusterServiceTemplate represents an optimization profile for an AIM
 * Contains metric type (latency/throughput) and GPU requirements
 */
export type AIMClusterServiceTemplate = {
  metadata: {
    name: string;
    labels: Record<string, string>;
  };
  spec: {
    modelName: string;
    metric: AIMMetric.Latency | AIMMetric.Throughput;
  };
  status: {
    status: 'Ready' | 'NotAvailable';
    /** Runtime profile from discovery. */
    profile?: {
      metadata?: AIMClusterServiceTemplateProfileMetadata;
    };
  };
};

/**
 * Namespace-scoped AIMServiceTemplate CRD resource.
 *
 * Returned by GET /namespaces/{namespace}/models/{model_name}/templates.
 * Represents a deployment configuration template for a fine-tuned AIMModel,
 * auto-created by the AIM Engine when the model is ready.
 */
export type AIMNamespaceServiceTemplate = {
  metadata: { name: string };
  spec: {
    modelName: string;
    metric: string | null;
    precision: string | null;
  };
  status: Record<string, unknown>;
};

/**
 * Complete AIM image metadata structure
 */
export type AIMImageMetadata = {
  model: {
    canonicalName: string;
    descriptionFull?: string;
    hfTokenRequired: boolean | null;
    source: string;
    tags: string[];
    title: string;
    variants: string[];
  };
  oci?: {
    description?: string;
    version?: string;
    title?: string;
    licenses?: string;
    vendor?: string;
    authors?: string;
    source?: string;
    documentation?: string;
    created?: string;
    revision?: string;
  };
};

export interface AimServiceReplica {
  metadata: {
    name: string;
    creationTimestamp?: string;
  };
  status?: {
    phase?: string;
    podIp?: string;
    containerStatuses?: {
      ready?: boolean;
      restartCount?: number;
      state?: Record<string, unknown>;
    }[];
    conditions?: {
      type?: string;
      status?: string;
      reason?: string;
      message?: string;
    }[];
  };
  spec?: {
    nodeName?: string;
    containers?: {
      resources?: {
        limits?: Record<string, string>;
      };
    }[];
  };
}
