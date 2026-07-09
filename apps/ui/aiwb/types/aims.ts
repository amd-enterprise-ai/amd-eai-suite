// Copyright © Advanced Micro Devices, Inc., or its affiliates.

// SPDX-License-Identifier: MIT

import type { OnboardPhase } from './custom-models';

/** Label set on AIMService resources backed by a namespace-scoped fine-tuned AIMModel. */
export const FINE_TUNED_LABEL = 'aiwb.apps.eai.amd.com/fine-tuned';

/** Label set on AIMService resources backed by a namespace-scoped AIMModel (fine-tuned or custom-imported). */
export const NAMESPACE_AIM_MODEL_LABEL =
  'aiwb.apps.eai.amd.com/namespace-aim-model';

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
 * Annotations stamped by the custom-model onboarding flow on AIMModel CRs.
 * Their presence on a catalog AIM marks it as user-imported (rather than a
 * stock AIM published to the cluster), which is what the Custom Models tab
 * filters on.
 *
 * Mirrors the API-side constants in `apps/api/aiwb/app/custom_models/constants.py`,
 * which build these from the default `AIWB_METADATA_PREFIX="aiwb.apps.eai.amd.com"`
 * and `EAI_APPS_METADATA_PREFIX="airm.silogen.ai"` (apps/api/aiwb/app/config.py).
 * Deployments that override either env var must keep the UI prefix in sync.
 */
export const AIM_DISPLAY_NAME_ANNOTATION = 'aiwb.apps.eai.amd.com/display-name';

export const SOURCE_URI_ANNOTATION = 'airm.silogen.ai/source-uri' as const;

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

/**
 * Free-form K8s annotations as carried on the AIMClusterModel CR. Always
 * include the well-known image-source annotations (`aim.eai.amd.com/...`),
 * and optionally include onboarding annotations for user-imported models
 * (see `custom_models/constants.py`).
 */
export type AIMClusterModelMetadataAnnotations = Record<string, string>;

export type AcceleratorType = 'cpu' | 'gpu';

export type DiscoveredProfileHardwareGroup = {
  /** Loose at the wire to round-trip unknown future engine values; the parser narrows to {@link AcceleratorType}. */
  acceleratorType?: string | null;
  acceleratorModel?: string | null;
  acceleratorCount?: number | null;
  supported?: boolean;
  hardwareSummary?: string | null;
  profiles?: Array<Record<string, unknown>>;
};

export type DiscoveredProfileCounts = {
  total?: number | null;
  supported?: number | null;
  unsupported?: number | null;
  byHardware?: DiscoveredProfileHardwareGroup[];
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
    /** Canonical model architecture identifier resolved by the v1alpha2 controller. */
    aimId?: string | null;
    imageMetadata: AIMImageMetadata;
    discoveredProfiles?: DiscoveredProfileCounts;
  };
};

/** Weights source entry as carried on an AIMModel spec (flat or profile override). */
export type AIMModelSource = {
  modelId: string;
  sourceUri: string;
  env?: {
    name: string;
    value?: string;
    valueFrom?: Record<string, unknown>;
  }[];
};

/**
 * Project-scoped fine-tuned AIMModel as returned by both the single-item
 * GET /v1/projects/{project}/fine-tuning/models/{model_id} and the list
 * endpoint GET /v1/projects/{project}/fine-tuning/models. Same payload, single
 * type.
 *
 * v1alpha2 imported / re-finetuned models carry their weights under
 * `spec.profiles.overrides.modelSources`; official and fine-tuning-published
 * models use the legacy flat `spec.modelSources`. Read both via
 * `resolveBaseModelSource` (lib/app/aims.ts) rather than reaching into one
 * field directly.
 */
export interface AIMModel {
  metadata: {
    name: string;
    namespace?: string | null;
    uid?: string;
    creationTimestamp: string;
    labels?: Record<string, string>;
    annotations?: Record<string, string>;
    ownerReferences?: {
      apiVersion: string;
      blockOwnerDeletion?: boolean;
      kind: string;
      name: string;
      uid: string;
    }[];
  };
  spec: {
    /** Container image. Absent for fine-tuned models (no published image). */
    image?: string;
    /** Legacy flat weights source. See {@link resolveBaseModelSource}. */
    modelSources?: AIMModelSource[];
    profiles?: {
      derivedFrom?: {
        selector?: {
          modelRef?: { name: string; scope?: string };
          role?: string;
        };
      };
      overrides?: {
        aimId?: string;
        modelId?: string;
        image?: string;
        modelSources?: AIMModelSource[];
      };
      versionPolicy?: string;
    };
    resources?: Record<string, unknown>;
  };
  status?: {
    status: string;
    /** Canonical model architecture identifier (matches AIMProfile spec.aimId). */
    aimId?: string | null;
    sourceType?: string;
    conditions?: AIMServiceCondition[];
    imageMetadata?: {
      model?: {
        canonicalName?: string;
        descriptionFull?: string;
        hfTokenRequired?: boolean | null;
        source?: string;
        tags?: string[];
        title?: string;
        variants?: string[];
      };
      oci?: {
        created?: string;
        description?: string;
        licenses?: string;
        revision?: string;
        source?: string;
        title?: string;
        vendor?: string;
        version?: string;
      };
      originalLabels?: Record<string, string>;
    };
    /** Hardware-grouped discovery breakdown emitted by aim-engine. */
    discoveredProfiles?: DiscoveredProfileCounts;
  };
}

/**
 * Mirrors aim-engine's AIMResolvedReference (v1alpha1 API ref). All fields
 * optional; the engine populates them when the source resource is known.
 * `scope` is the key disambiguator for namespace-vs-cluster lookups —
 * consumers should branch on it instead of probing both endpoints.
 */
export type ResolvedRef = {
  name?: string;
  namespace?: string;
  scope?: 'Namespace' | 'Cluster' | 'Merged' | 'Unknown';
  kind?: string;
  uid?: string;
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
  /** Selector for the resolved AIMProfile/AIMClusterProfile. Backend stores this loose; FE only ever reads `name`. */
  profile?: { name: string } | null;
  /** Per-service overrides on the resolved profile (engineArgs, containerEnv). */
  profileOverrides?: Record<string, unknown>;
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
    /**
     * Reference to the resolved AIMClusterModel/AIMModel. The semantics of
     * `name` differ between engine reconcilers — v1alpha1 sets the resource
     * name, v1alpha2 profile pipeline sets the canonical model id. For
     * resource-name lookups, prefer `spec.model.name` (the user-supplied
     * AIMClusterModel name, stable across pipelines).
     */
    resolvedModel?: ResolvedRef;
    /**
     * Reference to the resolved AIMProfile/AIMClusterProfile. Consumers that
     * need accelerator / precision / metric details fetch the profile via
     * the catalog endpoints — `scope` tells you which one to target.
     */
    resolvedProfile?: ResolvedRef;
  };
  clusterAuthGroupId: string | null;
  endpoints: {
    internal: string;
    external?: string;
  };
};

export type ParsedAIM = {
  model: string;
  /**
   * Canonical model architecture identifier (e.g. `CohereLabs/command-a-reasoning-08-2025`).
   * Sourced from the AIM's `status.aimId`; null until the engine has reconciled.
   */
  aimId: string | null;
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
  acceleratorTypes?: AcceleratorType[];
  status: AIMStatus | string;
  workloadStatuses: AIMWorkloadStatus[];
  isPreview: boolean;
  isHfTokenRequired: boolean;
  isLatest?: boolean;
  /**
   * True when the AIM was onboarded by a user via the custom-model import
   * wizard (vs. a stock AIM published to the cluster). Derived from the
   * presence of the {@link MODEL_DISPLAY_NAME_ANNOTATION} or
   * {@link SOURCE_URI_ANNOTATION} on the AIMModel CR. Optional so existing
   * `ParsedAIM` test fixtures don't all need to set it; the parser always
   * populates it.
   */
  isCustomImport?: boolean;
  /** Source URI captured at onboarding (e.g. a Hugging Face URL), when known. */
  sourceUri?: string;
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
    /**
     * True when at least one version in the family is user-onboarded.
     * Optional for the same reason as {@link ParsedAIM.isCustomImport};
     * `transformToAggregatedAIMs` always populates it.
     */
    isCustomImport?: boolean;
    tags: string[];
    acceleratorTypes?: AcceleratorType[];
    description: {
      short: string;
      full: string;
    };
    /**
     * Onboarding lifecycle phase for user-imported (BYOM) custom models.
     * Absent for stock AIM catalog models.
     */
    onboardPhase?: OnboardPhase;
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
  displayName?: string;
  replicas?: number;
  imagePullSecrets?: string[];
  hfToken?: string;
  metric?: string;

  // Autoscaling configuration
  minReplicas?: number;
  maxReplicas?: number;
  autoScaling?: AutoscalingPolicyConfig;

  // AIMServiceOverrides / profile selection (advanced profile params)
  precision?: string;
  gpuModel?: string;
  gpuCount?: number;
  profileName?: string;
};

/** Deploy body for custom/BYOM models — runtime profile comes from onboarding, not deploy. */
export type CustomModelDeployPayload = Pick<
  AIMDeployPayload,
  | 'model'
  | 'displayName'
  | 'replicas'
  | 'minReplicas'
  | 'maxReplicas'
  | 'autoScaling'
>;

/** Profile fields excluded from custom-model deploy payloads; runtime config lives on the namespace AIMProfile. */
export const AIM_DEPLOY_PROFILE_OVERRIDE_KEYS = [
  'metric',
  'precision',
  'gpuModel',
  'gpuCount',
  'profileName',
  'imagePullSecrets',
  'hfToken',
] as const satisfies ReadonlyArray<keyof AIMDeployPayload>;

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

/** Canonical `spec.type` value on AIMClusterProfile/AIMProfile. Only 'optimized' is treated as optimized. */
export const AIM_PROFILE_TYPE_OPTIMIZED = 'optimized' as const;

/**
 * AIMClusterProfile / AIMProfile spec — flat metadata on the profile resource itself.
 * Mirrors the backend `AIMProfileSpec` (see apps/api/aiwb/app/aims/crds.py).
 *
 * Field renames vs. v1alpha1: `gpu` → `acceleratorModel`, `gpuCount` → `acceleratorCount`.
 * New: `acceleratorType` ('gpu' | 'cpu') and `primary` (preferred profile flag).
 */
export type AIMProfileSpec = {
  modelName?: string;
  metric?: AIMMetric.Latency | AIMMetric.Throughput | string | null;
  type?: 'optimized' | 'preview' | 'unoptimized' | string;
  engine?: string;
  acceleratorModel?: string;
  acceleratorType?: 'gpu' | 'cpu' | string;
  acceleratorCount?: number;
  precision?: string;
  primary?: boolean;
};

/** Status fields on AIMClusterProfile/AIMProfile. */
export type AIMProfileStatusFields = {
  status?: 'Ready' | 'NotAvailable' | string;
  version?: string;
  matchingNodes?: number;
  /** Human-readable summary like "1 x MI300X" or "CPU". */
  hardwareSummary?: string;
};

/**
 * Cluster-scoped AIMClusterProfile CRD resource.
 * Returned by GET /inference/models/{name}/profiles.
 */
export type AIMClusterProfile = {
  metadata: {
    name: string;
    labels?: Record<string, string>;
  };
  spec: AIMProfileSpec;
  status: AIMProfileStatusFields;
};

/**
 * Namespace-scoped AIMProfile CRD resource.
 * Returned by GET /projects/{project}/models/{model_name}/profiles.
 */
export type AIMProfile = {
  metadata: {
    name: string;
    labels?: Record<string, string>;
  };
  spec: AIMProfileSpec;
  status: AIMProfileStatusFields;
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

/**
 * Per-pod status for a single inference deployment replica.
 *
 * Mirrors backend `InferenceReplicaResponse` (camelCase wire format) returned
 * by GET /v1/projects/{project}/inference/{id}/replicas. Field shape matches
 * Kubernetes pod status fields with one explicit override: `podIp` (the
 * backend serializes K8s `podIP` to standard camelCase).
 */
export interface InferenceReplica {
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
