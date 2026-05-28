// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { AIMServiceCondition } from '@/types/aims';

export enum ModelOnboardingStatus {
  READY = 'ready',
  PENDING = 'pending',
  FAILED = 'failed',
}

export type ModelFinetuneParams = {
  name: string;
  datasetId: string;
  epochs?: number;
  learningRate?: number;
  batchSize?: number;
  hfTokenSecretName?: string;
};

export interface Model {
  id?: string;
  name: string;
  canonicalName: string;
  createdAt?: string;
  onboardingStatus?: ModelOnboardingStatus;
  createdBy?: string;
  modelWeightsPath?: string | null;
  /** Kubernetes resource name (AIMModel CR name or fine-tuning Job name). */
  resourceName?: string;
  /** WorkloadStatus value for K8s-sourced models (e.g., 'Pending', 'Running', 'Complete'). */
  status?: string;
  /** Workload UUID tracked in AIWB. */
  workloadId?: string;
}

/** Raw response shape returned by GET /namespaces/{ns}/aims/models. */
export interface AIMModelResponse {
  metadata: {
    name: string;
    creationTimestamp: string;
    labels?: Record<string, string>;
  };
  spec: {
    aimId?: string;
    image: string;
    modelSources: { modelId: string; sourceUri: string }[];
    custom?: {
      versionPolicy?: string;
    };
    env?: {
      name: string;
      value?: string;
      valueFrom?: Record<string, unknown>;
    }[];
  };
  status?: {
    status: string;
    sourceType?: string;
    conditions?: AIMServiceCondition[];
    imageMetadata?: {
      model?: {
        canonicalName?: string;
        descriptionFull?: string;
        hfTokenRequired?: boolean;
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
  };
}

export interface ModelRequirements {
  minGpuCount: number;
  minGpuMemoryGb: number;
  minCpuCores: number;
  minRamGb: number;
  minStorageGb: number;
}

export interface InferenceSettings {
  systemPrompt: string;
  temperature: number;
  frequencyPenalty: number;
  presencePenalty: number;
}

export interface FinetunableModel {
  canonicalName: string;
  gpuCount: number | null;
  compatibleAccelerators: string[];
  compatibleAcceleratorNames: string[];
}

export const DEFAULT_SETTINGS: InferenceSettings = {
  systemPrompt: '',
  temperature: 0,
  frequencyPenalty: 0,
  presencePenalty: 0,
};
