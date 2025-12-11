// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

export enum ModelOnboardingStatus {
  READY = 'ready',
  PENDING = 'pending',
  FAILED = 'failed',
}

export type ModelFinetuneParams = {
  name: string;
  datasetId: string;
  epochs: number;
  learningRate: number;
  batchSize: number;
  hfTokenSecretId?: string;
};

export interface Model {
  id: string;
  name: string;
  canonicalName: string;
  createdAt: string;
  onboardingStatus: ModelOnboardingStatus;
  createdBy: string;
  modelWeightsPath: string | null;
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

export const DEFAULT_SETTINGS: InferenceSettings = {
  systemPrompt: '',
  temperature: 0,
  frequencyPenalty: 0,
  presencePenalty: 0,
};
