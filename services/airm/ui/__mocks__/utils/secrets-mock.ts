// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import {
  ProjectSecretStatus,
  SecretScope,
  SecretStatus,
  SecretType,
} from '@/types/enums/secrets';
import {
  ProjectSecret,
  ProjectSecretWithParentSecret,
  Secret,
} from '@/types/secrets';

export const generateMockSecrets = (n: number): Secret[] => {
  return Array.from({ length: n }, (_, i) => ({
    id: `secret-${i + 1}`,
    name: `My Secret ${i + 1}`,
    displayName: `My Secret Display Name ${i + 1}`,
    type: SecretType.EXTERNAL,
    status: SecretStatus.PENDING,
    statusReason: '',
    scope: SecretScope.ORGANIZATION,
    projectSecrets: generateMockProjectSecrets(1),
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }));
};

export const generateMockProjectSecrets = (
  n: number,
  projectId?: string,
): ProjectSecret[] => {
  return Array.from({ length: n }, (_, i) => ({
    id: `project-secret-${i + 1}`,
    name: `My Project ${i + 1}`,
    projectId: projectId ?? `project-${i + 1}`,
    projectName: `Project Name ${i + 1}`,
    displayName: `My Project Display Name ${i + 1}`,
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
    name: `My project secret ${i + 1}`,
    projectId: projectId ?? `project-${i + 1}`,
    projectName: `Project Name ${i + 1}`,
    displayName: `My Project Display Name ${i + 1}`,
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
