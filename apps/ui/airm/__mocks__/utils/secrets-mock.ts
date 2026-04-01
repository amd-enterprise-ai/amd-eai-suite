// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import {
  ProjectSecretStatus,
  SecretScope,
  SecretStatus,
  SecretType,
  SecretUseCase,
} from '@amdenterpriseai/types';
import {
  ProjectSecret,
  ProjectSecretWithParentSecret,
  Secret,
} from '@amdenterpriseai/types';
import { ProjectStatus } from '@amdenterpriseai/types';

export const generateMockSecrets = (n: number): Secret[] => {
  return Array.from({ length: n }, (_, i) => ({
    id: `secret-${i + 1}`,
    name: `My Secret ${i + 1}`,
    displayName: `My Secret Display Name ${i + 1}`,
    type: SecretType.EXTERNAL_SECRET,
    status: SecretStatus.PENDING,
    statusReason: '',
    useCase: SecretUseCase.GENERIC,
    scope: SecretScope.ORGANIZATION,
    projectSecrets: generateMockProjectSecrets(1),
    createdAt: new Date().toISOString(),
    createdBy: 'user@example.com',
    updatedBy: 'user@example.com',
    updatedAt: new Date().toISOString(),
  }));
};

export const generateMockProjectSecrets = (
  n: number,
  projectId?: string,
): ProjectSecret[] => {
  return Array.from({ length: n }, (_, i) => ({
    id: `project-secret-${i + 1}`,
    project: {
      id: projectId ?? `project-${i + 1}`,
      name: `project-name-${i + 1}`,
      description: `Project Description ${i + 1}`,
      status: ProjectStatus.READY,
      statusReason: null,
      clusterId: `cluster-${i + 1}`,
    },
    scope: SecretScope.PROJECT,
    status: ProjectSecretStatus.PENDING,
    statusReason: '',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    createdBy: `user-${i + 1}`,
    updatedBy: `user-${i + 1}`,
  }));
};

export const generateMockProjectSecretsWithParentSecret = (
  n: number,
  projectId?: string,
): ProjectSecretWithParentSecret[] => {
  return Array.from({ length: n }, (_, i) => ({
    id: `project-secret-${i + 1}`,
    project: {
      id: projectId ?? `project-${i + 1}`,
      name: `project-name-${i + 1}`,
      description: `Project Description ${i + 1}`,
      status: ProjectStatus.READY,
      statusReason: null,
      clusterId: `cluster-${i + 1}`,
    },
    scope: SecretScope.PROJECT,
    status: ProjectSecretStatus.PENDING,
    statusReason: '',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    createdBy: `user-${i + 1}`,
    updatedBy: `user-${i + 1}`,
    secret: generateMockSecrets(1)[0],
  }));
};
