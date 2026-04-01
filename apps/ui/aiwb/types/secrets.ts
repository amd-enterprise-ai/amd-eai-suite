// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { SecretUseCase } from '@amdenterpriseai/types';

export type SecretResponseData = {
  metadata: SecretMetadata;
  useCase: SecretUseCase;
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
  name: string;
  data: Record<string, string>;
  use_case: SecretUseCase;
};

export type SecretDataEntry = {
  key: string;
  value: string;
};

export type CreateSecretForm = {
  name: string;
  useCase: SecretUseCase;
  key?: string;
  value?: string;
  dataEntries?: SecretDataEntry[];
};
