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
  createdBy: string;
  updatedBy: string;
};

export type Secret = BaseSecret & {
  projectSecrets: ProjectSecret[];
};

export type ProjectSecretWithParentSecret = ProjectSecret & {
  secret: BaseSecret;
};

export type AddSecretFormData = {
  type: SecretType;
  context: SecretUseCase;
  manifest: string;
  name?: string;
  token?: string;
  projectIds: string[];
};

export type AssignSecretFormData = {
  projectIds: string[];
};

export type AssignOrgSecretToProjectFormData = {
  secretId: string;
};

export type SecretsResponse = {
  secrets: Secret[];
};

export type ProjectSecretsResponse = {
  projectSecrets: ProjectSecretWithParentSecret[];
};

type SecretBaseRequest = {
  type: SecretType;
  name: string;
  scope: SecretScope;
  use_case?: SecretUseCase;
  manifest: string;
};

export type CreateSecretRequest = SecretBaseRequest & {
  project_ids: string[];
};

export type CreateProjectSecretRequest = SecretBaseRequest;

export type AssignSecretRequest = {
  project_ids: string[];
};

export type HuggingFaceTokenData = {
  selectedToken?: string;
  name?: string;
  token?: string;
};
