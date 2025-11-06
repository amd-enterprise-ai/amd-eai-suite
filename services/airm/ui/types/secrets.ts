// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  ProjectSecretStatus,
  SecretScope,
  SecretStatus,
  SecretType,
  SecretUseCase,
} from './enums/secrets';

export type ProjectSecret = {
  id: string;
  projectId: string;
  projectName: string;
  scope: SecretScope;
  status: ProjectSecretStatus;
  statusReason: string | null;
  createdAt: string;
  createdBy: string;
  updatedAt: string;
  updatedBy: string;
};

export type BaseSecret = {
  displayName: string;
  id: string;
  name: string;
  type: SecretType;
  useCase?: SecretUseCase;
  status: SecretStatus;
  statusReason: string | null;
  scope: SecretScope;
  createdAt: string;
  updatedAt: string;
};

export type Secret = BaseSecret & {
  projectSecrets: ProjectSecret[];
};

export type ProjectSecretWithParentSecret = ProjectSecret & {
  secret: BaseSecret;
};

export type AddSecretFormData = {
  type: SecretType;
  manifest: string;
  projectIds: string[];
};

export type AssignSecretFormData = {
  projectIds: string[];
};

export type AssignSecretToProjectFormData = {
  secretId: string;
};

export type SecretsResponse = {
  secrets: Secret[];
};

export type ProjectSecretsResponse = {
  projectSecrets: ProjectSecretWithParentSecret[];
};

export type CreateSecretRequest = {
  type: SecretType;
  name: string;
  scope: SecretScope;
  use_case?: SecretUseCase;
  manifest: string;
  project_ids: string[];
};

export type AssignSecretRequest = {
  project_ids: string[];
};

export type HuggingFaceTokenData = {
  selectedToken?: string;
  name?: string;
  token?: string;
};
