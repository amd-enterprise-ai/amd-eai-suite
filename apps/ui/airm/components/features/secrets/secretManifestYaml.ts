// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  EXTERNAL_SECRETS_API_GROUP,
  EXTERNAL_SECRETS_KIND,
  KUBERNETES_SECRETS_KIND,
  KUBERNETES_SECRETS_VERSION,
  nameRegex,
} from './constants';

import { parseAllDocuments } from 'yaml';

export type ManifestYamlValidationSuccess = {
  ok: true;
  manifest: Record<string, unknown>;
};

export type ManifestYamlValidationFailure = {
  ok: false;
  error: string;
};

export type ManifestYamlValidationResult =
  | ManifestYamlValidationSuccess
  | ManifestYamlValidationFailure;

function manifestYamlValidator(
  expectedApiVersion: string | ((apiVersion: string) => boolean),
  expectedKind: string,
): (value: string) => ManifestYamlValidationResult {
  return (value: string) => {
    try {
      const yamls = parseAllDocuments(value);
      if (!Array.isArray(yamls) || yamls.length !== 1) {
        return {
          ok: false,
          error: 'form.add.field.manifest.error.yaml.multiple',
        };
      }
      const yamlDoc = yamls[0];
      const yaml = (yamlDoc?.toJSON?.() ?? {}) as Record<string, unknown>;

      const isValidApiVersion =
        typeof expectedApiVersion === 'function'
          ? expectedApiVersion(String(yaml?.apiVersion ?? ''))
          : yaml?.apiVersion === expectedApiVersion;

      if (!yaml || !yaml.apiVersion || !isValidApiVersion) {
        return {
          ok: false,
          error:
            typeof expectedApiVersion === 'function'
              ? 'form.add.field.manifest.error.yaml.incorrectGroup'
              : 'form.add.field.manifest.error.yaml.incorrectVersion',
        };
      }

      if (!yaml || yaml.kind !== expectedKind) {
        return {
          ok: false,
          error: 'form.add.field.manifest.error.yaml.incorrectKind',
        };
      }

      const metadata = yaml.metadata as { name?: unknown } | undefined;
      if (
        !metadata ||
        typeof metadata.name !== 'string' ||
        metadata.name.length === 0
      ) {
        return {
          ok: false,
          error: 'form.add.field.manifest.error.yaml.noName',
        };
      }

      if (!nameRegex.test(metadata.name)) {
        return {
          ok: false,
          error: 'form.add.field.manifest.error.yaml.invalidName',
        };
      }

      return { ok: true, manifest: yaml };
    } catch {
      return {
        ok: false,
        error: 'form.add.field.manifest.error.yaml.malformed',
      };
    }
  };
}

function isExternalSecretsApiGroup(apiVersion: string): boolean {
  if (!apiVersion) {
    return false;
  }
  const [group] = apiVersion.split('/');
  return group === EXTERNAL_SECRETS_API_GROUP;
}

export function createManifestYamlValidators() {
  const validateExternalSecretYaml = manifestYamlValidator(
    isExternalSecretsApiGroup,
    EXTERNAL_SECRETS_KIND,
  );
  const validateKubernetesSecretYaml = manifestYamlValidator(
    KUBERNETES_SECRETS_VERSION,
    KUBERNETES_SECRETS_KIND,
  );
  return { validateExternalSecretYaml, validateKubernetesSecretYaml };
}
