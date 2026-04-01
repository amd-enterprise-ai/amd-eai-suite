// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  ProjectSecretStatus,
  SecretScope,
  SecretStatus,
  SecretType,
} from '@amdenterpriseai/types';
import { ProjectSecret, Secret } from '@amdenterpriseai/types';

export const doesSecretDataNeedToBeRefreshed = (secrets: Secret[]) => {
  if (!secrets || !Array.isArray(secrets)) {
    return false;
  }

  return secrets.some(
    (c) =>
      c.status == SecretStatus.PENDING ||
      c.status == SecretStatus.PARTIALLY_SYNCED ||
      c.status == SecretStatus.DELETING,
  );
};

export const doesProjectSecretDataNeedToBeRefreshed = (
  secrets: ProjectSecret[],
) => {
  if (!secrets || !Array.isArray(secrets)) {
    return false;
  }

  return secrets.some(
    (c) =>
      c.status == ProjectSecretStatus.PENDING ||
      c.status == ProjectSecretStatus.DELETING,
  );
};

export const isSecretActioning = (secret: Secret) => {
  return (
    secret.status === SecretStatus.DELETING ||
    secret.status === SecretStatus.PENDING
  );
};

export const isDuplicateSecret = (
  secrets: Secret[],
  secretName: string,
  secretType: SecretType,
  scope: SecretScope,
  projectId?: string,
): boolean => {
  return secrets.some((secret) => {
    // Must have same name
    if (secret.name !== secretName) return false;

    // Must have same type
    if (secret.type !== secretType) return false;

    // Must have same scope
    if (secret.scope !== scope) return false;

    if (secret.scope === SecretScope.PROJECT && projectId) {
      // For project-scoped secrets: check if in same project
      return secret.projectSecrets?.some((ps) => ps.project.id === projectId);
    } else {
      // For organization-scoped secrets: any org secret with same name+type is duplicate
      return secret.scope === SecretScope.ORGANIZATION;
    }
  });
};
