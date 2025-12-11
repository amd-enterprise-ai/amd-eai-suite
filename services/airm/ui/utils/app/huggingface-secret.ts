// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { SecretScope, SecretType, SecretUseCase } from '@/types/enums/secrets';
import {
  CreateSecretRequest,
  ProjectSecretWithParentSecret,
} from '@/types/secrets';
import { z } from 'zod';

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

/**
 * Configuration for HuggingFace token validation
 */
export interface HuggingFaceValidationConfig {
  /** Whether HuggingFace token is required */
  isRequired: boolean;
  /** Project secrets to check for duplicates */
  projectSecrets?: ProjectSecretWithParentSecret[];
  /** Translation function for validation messages */
  t: (key: string, options?: any) => string;
}

/**
 * Shared validation logic for HuggingFace token fields.
 * This can be used in superRefine to validate the token selector fields.
 *
 * @param data - The form data containing selectedToken, tokenName, and token fields
 * @param ctx - The Zod refinement context to add issues to
 * @param config - Configuration for validation behavior
 *
 * @example
 * ```typescript
 * const schema = z.object({
 *   selectedToken: z.string().optional(),
 *   tokenName: z.string().optional(),
 *   token: z.string().optional(),
 * }).superRefine((data, ctx) => {
 *   validateHuggingFaceTokenFields(data, ctx, {
 *     isRequired: true,
 *     projectSecrets,
 *     t
 *   });
 * });
 * ```
 */
export const validateHuggingFaceTokenFields = (
  data: {
    selectedToken?: string;
    tokenName?: string;
    token?: string;
  },
  ctx: z.RefinementCtx,
  config: HuggingFaceValidationConfig,
): void => {
  const { isRequired, projectSecrets, t } = config;

  // Skip validation if not required
  if (!isRequired) return;

  const hasSelectedToken =
    data.selectedToken && data.selectedToken.trim() !== '';
  const hasTokenName = data.tokenName && data.tokenName.trim() !== '';
  const hasToken = data.token && data.token.trim() !== '';

  // If user selected an existing token, validation passes
  if (hasSelectedToken) return;

  // If no token is selected and no new token info provided
  if (!hasTokenName && !hasToken) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: t('huggingFaceTokenDrawer.validation.tokenRequired'),
      path: ['selectedToken'],
    });
    return;
  }

  // Validate token name
  if (!hasTokenName) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: t('huggingFaceTokenDrawer.validation.nameRequired'),
      path: ['tokenName'],
    });
  } else if (hasTokenName) {
    // Validate token name pattern
    const tokenNamePattern = /^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$/;
    if (!tokenNamePattern.test(data.tokenName!.trim())) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: t('huggingFaceTokenDrawer.validation.invalidSecretName'),
        path: ['tokenName'],
      });
    }

    // Check for duplicate name+type in project
    if (projectSecrets) {
      const isDuplicate = projectSecrets.some(
        (ps) =>
          ps.secret.name === data.tokenName!.trim() &&
          ps.secret.type === SecretType.KUBERNETES_SECRET,
      );

      if (isDuplicate) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: t('huggingFaceTokenDrawer.validation.duplicateSecretName'),
          path: ['tokenName'],
        });
      }
    }
  }

  // Validate token
  if (!hasToken) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: t('huggingFaceTokenDrawer.validation.tokenRequired'),
      path: ['token'],
    });
  } else if (!isValidHuggingFaceToken(data.token!)) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: t('huggingFaceTokenDrawer.validation.invalidTokenFormat'),
      path: ['token'],
    });
  }
};
