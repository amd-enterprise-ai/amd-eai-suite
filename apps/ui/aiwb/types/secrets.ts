// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { SecretUseCase } from '@amdenterpriseai/types';

export type SecretResponseData = {
  metadata: SecretMetadata;
  useCase: SecretUseCase;
  displayName: string;
};

type SecretMetadata = {
  name: string;
  namespace: string;
  uid?: string;
  labels?: Record<string, string>;
  annotations?: Record<string, string>;
  creationTimestamp: string;
};

export type CreateSecretRequest = {
  displayName: string;
  data: Record<string, string>;
  useCase: SecretUseCase;
};

export type SecretDataEntry = {
  key: string;
  value: string;
};

export type CreateSecretForm = {
  displayName: string;
  useCase: SecretUseCase;
  key?: string;
  value?: string;
  dataEntries?: SecretDataEntry[];
};

export type HuggingFaceTokenData = {
  selectedToken?: string;
  name?: string;
  token?: string;
};
