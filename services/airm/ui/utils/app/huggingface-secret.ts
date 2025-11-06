// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { SecretScope, SecretType, SecretUseCase } from '@/types/enums/secrets';
import { CreateSecretRequest } from '@/types/secrets';

export const generateHuggingFaceSecretManifest = (
  secretName: string,
  token: string,
): string => {
  const encodedToken = Buffer.from(token, 'utf-8').toString('base64');

  const manifest = {
    apiVersion: 'v1',
    kind: 'Secret',
    metadata: {
      name: secretName,
    },
    type: 'Opaque',
    data: {
      token: encodedToken,
    },
  };

  return JSON.stringify(manifest, null, 2);
};

export const createHuggingFaceSecretRequest = (
  name: string,
  token: string,
  projectIds: string[],
): CreateSecretRequest => {
  // Name should already be validated by the form - no transformation needed
  const manifest = generateHuggingFaceSecretManifest(name, token);

  return {
    name,
    type: SecretType.KUBERNETES_SECRET,
    scope: SecretScope.PROJECT,
    use_case: SecretUseCase.HUGGING_FACE,
    manifest,
    project_ids: projectIds,
  };
};

export const isValidHuggingFaceToken = (token: string): boolean => {
  const hfTokenPattern = /^hf_[a-zA-Z0-9]{20,}$/;
  return hfTokenPattern.test(token);
};

export const isValidKubernetesSecretName = (name: string): boolean => {
  // Kubernetes secret name must:
  // - Be lowercase alphanumeric characters, '-' or '.'
  // - Start and end with an alphanumeric character
  // - Be at most 253 characters (though we'll allow any length for this validation)
  const k8sNamePattern = /^[a-z0-9]([-a-z0-9.]*[a-z0-9])?$/;
  return k8sNamePattern.test(name);
};
