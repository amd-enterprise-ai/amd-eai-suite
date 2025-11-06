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
  collectionId?: string;
  ragEnabled: boolean;
  hybridSearch: boolean;
  certainty: number;
  topK: number;
  alpha: number;
  systemPrompt: string;
  userPromptTemplate: string;
  temperature: number;
  frequencyPenalty: number;
  presencePenalty: number;
}

export const DEFAULT_SETTINGS: InferenceSettings = {
  collectionId: undefined,
  certainty: 0,
  topK: 4,
  alpha: 0.5,
  systemPrompt: '',
  userPromptTemplate: '',
  temperature: 0,
  ragEnabled: false,
  hybridSearch: false,
  frequencyPenalty: 0,
  presencePenalty: 0,
};
