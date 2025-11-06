// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { ProjectSecretStatus, SecretStatus } from '@/types/enums/secrets';
import { ProjectSecret, Secret } from '@/types/secrets';

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
