// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { isDuplicateSecret } from '@/utils/secrets';

import { AddSecretFormData } from '@/types/secrets';
import { SecretScope, SecretType } from '@/types/enums/secrets';
import { SecretUseCase } from '@amdenterpriseai/types';
import { Secret } from '@/types/secrets';

import { EXTERNAL_SECRETS_KIND, KUBERNETES_SECRETS_KIND } from './constants';
import type { ManifestYamlValidationResult } from './secretManifestYaml';

import { type ZodType, type ZodTypeDef, z } from 'zod';

const MALFORMED_YAML_KEY = 'form.add.field.manifest.error.yaml.malformed';

const EXTERNAL_MANIFEST_RESOURCE_KEY =
  'form.add.field.manifest.externalSecret.name';
const KUBERNETES_MANIFEST_RESOURCE_KEY = 'form.add.field.manifest.secret.name';

export type AddSecretTranslateFn = (
  key: string,
  options?: Record<string, unknown>,
) => string;

export type AddSecretFormSchemaParams = {
  t: AddSecretTranslateFn;
  secrets: Secret[];
  validateExternalSecretYaml: (value: string) => ManifestYamlValidationResult;
  validateKubernetesSecretYaml: (value: string) => ManifestYamlValidationResult;
};

function formatManifestYamlIssue(
  t: AddSecretTranslateFn,
  errorKey: string,
  resourceKey: string,
  kind: string | undefined,
): string {
  return t(errorKey, {
    resource: t(resourceKey),
    ...(kind !== undefined ? { kind } : {}),
  });
}

/**
 * Zod schema for the add-secret drawer. Kept in a separate module so validation
 * rules (including multi-issue behavior) are covered by unit tests without DOM.
 */
export function createAddSecretFormSchema({
  t,
  secrets,
  validateExternalSecretYaml,
  validateKubernetesSecretYaml,
}: AddSecretFormSchemaParams): ZodType<AddSecretFormData, ZodTypeDef, unknown> {
  return z
    .object({
      projectIds: z.preprocess((val: unknown) => {
        if (Array.isArray(val)) return val;
        if (typeof val === 'string' && val !== '') return val.split(',');
        return [];
      }, z.array(z.string())),
      manifest: z.string().optional(),
      scope: z.union([z.nativeEnum(SecretScope), z.undefined(), z.literal('')]),
      type: z.union([z.nativeEnum(SecretType), z.undefined(), z.literal('')]),
      useCase: z.union([
        z.nativeEnum(SecretUseCase),
        z.undefined(),
        z.literal(''),
      ]),
      name: z.string().optional(),
      token: z.string().optional(),
    })
    .superRefine((data, ctx) => {
      const scopeOk =
        data.scope !== undefined &&
        data.scope !== '' &&
        Object.values(SecretScope).includes(data.scope as SecretScope);
      if (!scopeOk) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: t('form.add.field.scope.error.required'),
          path: ['scope'],
        });
      }

      const typeOk =
        data.type !== undefined &&
        data.type !== '' &&
        Object.values(SecretType).includes(data.type as SecretType);
      if (!typeOk) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: t('form.add.field.type.error.required'),
          path: ['type'],
        });
      }

      const useCaseOk =
        data.useCase !== undefined &&
        data.useCase !== '' &&
        Object.values(SecretUseCase).includes(data.useCase as SecretUseCase);
      if (!useCaseOk) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: t('form.add.field.useCase.error.required'),
          path: ['useCase'],
        });
      }

      if (
        scopeOk &&
        data.scope === SecretScope.PROJECT &&
        data.projectIds.length === 0
      ) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: t('form.add.field.projectIds.error.required'),
          path: ['projectIds'],
        });
      }

      if (
        scopeOk &&
        data.scope === SecretScope.PROJECT &&
        useCaseOk &&
        data.useCase === SecretUseCase.S3
      ) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: t('form.add.field.useCase.error.s3NotAllowedForProject'),
          path: ['useCase'],
        });
      }

      const resourceKey =
        typeOk && data.type === SecretType.EXTERNAL_SECRET
          ? EXTERNAL_MANIFEST_RESOURCE_KEY
          : KUBERNETES_MANIFEST_RESOURCE_KEY;

      const manifestRaw = data.manifest ?? '';
      if (!manifestRaw || manifestRaw.trim().length < 2) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: t('form.add.field.manifest.error.required', {
            resource: t(resourceKey),
          }),
          path: ['manifest'],
        });
        return;
      }

      let validatedManifest: Record<string, unknown> | undefined;

      if (typeOk) {
        if (data.type === SecretType.EXTERNAL_SECRET) {
          const r = validateExternalSecretYaml(manifestRaw);
          if (!r.ok) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: formatManifestYamlIssue(
                t,
                r.error,
                EXTERNAL_MANIFEST_RESOURCE_KEY,
                r.error === MALFORMED_YAML_KEY
                  ? undefined
                  : EXTERNAL_SECRETS_KIND,
              ),
              path: ['manifest'],
            });
            return;
          }
          validatedManifest = r.manifest;
        } else {
          const r = validateKubernetesSecretYaml(manifestRaw);
          if (!r.ok) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: formatManifestYamlIssue(
                t,
                r.error,
                KUBERNETES_MANIFEST_RESOURCE_KEY,
                r.error === MALFORMED_YAML_KEY
                  ? undefined
                  : KUBERNETES_SECRETS_KIND,
              ),
              path: ['manifest'],
            });
            return;
          }
          validatedManifest = r.manifest;
        }
      } else {
        const extR = validateExternalSecretYaml(manifestRaw);
        const k8sR = validateKubernetesSecretYaml(manifestRaw);
        // Type unset: accept YAML that matches either format. If both fail, surface
        // the ExternalSecret validator error (stable choice for ambiguous YAML).
        if (!extR.ok && !k8sR.ok) {
          const errorKey = extR.error;
          const errResourceKey = EXTERNAL_MANIFEST_RESOURCE_KEY;
          const kind =
            errorKey === MALFORMED_YAML_KEY ? undefined : EXTERNAL_SECRETS_KIND;
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: formatManifestYamlIssue(t, errorKey, errResourceKey, kind),
            path: ['manifest'],
          });
          return;
        }
      }

      if (!typeOk) {
        return;
      }

      const metadata = validatedManifest?.metadata as
        | { name?: string }
        | undefined;
      const secretName = metadata?.name ?? '';

      const isDuplicate = scopeOk
        ? isDuplicateSecret(
            secrets,
            secretName,
            data.type as SecretType,
            data.scope as SecretScope,
            data.scope === SecretScope.PROJECT && data.projectIds?.[0]
              ? data.projectIds[0]
              : undefined,
          )
        : secrets.some(
            (s) =>
              s.name === secretName && s.type === (data.type as SecretType),
          );

      if (isDuplicate) {
        const secretTypeLabel = t(`secretType.${data.type}`);
        const scopeLabel = data.scope as SecretScope;

        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: t('form.add.field.manifest.error.yaml.duplicateName', {
            resource: t(resourceKey),
            secretType: secretTypeLabel,
            name: secretName,
            scope: scopeLabel,
          }),
          path: ['manifest'],
        });
      }
    })
    .transform(
      (data): AddSecretFormData => ({
        projectIds: data.projectIds,
        manifest: data.manifest ?? '',
        scope: data.scope as SecretScope,
        type: data.type as SecretType,
        useCase: data.useCase as SecretUseCase,
        name: data.name,
        token: data.token,
      }),
    );
}
