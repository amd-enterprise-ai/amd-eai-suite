// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export enum ModelOnboardingStatus {
  READY = 'ready',
  PENDING = 'pending',
  FAILED = 'failed',
}

export type ModelFinetuneParams = {
  displayName: string;
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
  /** Source URI of the model weights. */
  sourceUri?: string | null;
  /** Kubernetes resource name (AIMModel CR name or fine-tuning Job name). */
  resourceName?: string;
  /** WorkloadStatus value for K8s-sourced models (e.g., 'Pending', 'Running', 'Complete'). */
  status?: string;
  /** Workload UUID tracked in AIWB. */
  workloadId?: string;
  /** Whether fine-tuning this model needs a Hugging Face token. */
  hfTokenRequired?: boolean | null;
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
  /** Whether this recipe targets gated base weights. Null when the overlay does not declare it. */
  hfTokenRequired?: boolean | null;
}

export const DEFAULT_SETTINGS: InferenceSettings = {
  systemPrompt: '',
  temperature: 0,
  frequencyPenalty: 0,
  presencePenalty: 0,
};
