// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { SecretScope, SecretType, SecretUseCase } from '@amdenterpriseai/types';
import { CreateSecretRequest } from '@amdenterpriseai/types';
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

/**
 * Validates the format of a HuggingFace token.
 *
 * @param token - The token string to validate
 * @returns `true` if the token matches the HuggingFace format, `false` otherwise
 *
 * @remarks
 * Valid HuggingFace tokens must:
 * - Start with the prefix 'hf_'
 * - Followed by at least 20 alphanumeric characters (uppercase or lowercase)
 *
 * @example
 * ```typescript
 * isValidHuggingFaceToken('hf_abcdefghijklmnopqrstuvwxyz123456'); // true
 * isValidHuggingFaceToken('invalid_token'); // false
 * isValidHuggingFaceToken('hf_short'); // false (too short)
 * ```
 */
export const isValidHuggingFaceToken = (token: string): boolean => {
  const hfTokenPattern = /^hf_[a-zA-Z0-9]{20,}$/;
  return hfTokenPattern.test(token);
};

/**
 * Validates HuggingFace token fields in a form.
 *
 * Performs validation for the HuggingFace token selector component, ensuring that either
 * an existing token is selected or a new token is provided with valid name and format.
 *
 * @param data - The form data object containing token fields
 * @param data.selectedToken - Optional ID of an existing selected token
 * @param data.tokenName - Optional name for a new token (must match Kubernetes secret name pattern)
 * @param data.token - Optional new token value (must match HuggingFace token format: `hf_*`)
 * @param ctx - Zod refinement context for adding validation errors
 * @param t - Translation function for error messages
 *
 * @remarks
 * Validation rules:
 * - Either `selectedToken` must be provided, OR both `tokenName` and `token` must be provided
 * - Token name must match pattern: lowercase alphanumeric with dots and hyphens (Kubernetes format)
 * - Token must match HuggingFace format: starts with 'hf_' followed by 20+ alphanumeric characters
 *
 * ```
 */
export const validateHuggingFaceTokenFields = (
  data: {
    tokenName?: string;
    token?: string;
  },
  ctx: z.RefinementCtx,
  t: (key: string) => string,
): void => {
  const hasTokenName = data.tokenName && data.tokenName.trim() !== '';
  const hasToken = data.token && data.token.trim() !== '';

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
