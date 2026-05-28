// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ProjectBasicInfo } from './projects';
import {
  ProjectSecretStatus,
  SecretScope,
  SecretStatus,
  SecretType,
} from './enums/secrets';

import { SecretUseCase } from '@amdenterpriseai/types';

export type ProjectSecret = {
  id: string;
  project: ProjectBasicInfo;
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
  scope: SecretScope;
  useCase: SecretUseCase;
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
  data: Secret[];
};

export type ProjectSecretsResponse = {
  data: ProjectSecretWithParentSecret[];
};

type SecretBaseRequest = {
  type: SecretType;
  name: string;
  scope: SecretScope;
  useCase?: SecretUseCase;
  manifest: string;
};

export type CreateSecretRequest = SecretBaseRequest & {
  projectIds: string[];
};

export type CreateProjectSecretRequest = SecretBaseRequest;

export type AssignSecretRequest = {
  projectIds: string[];
};
