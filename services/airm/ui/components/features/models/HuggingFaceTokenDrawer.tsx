// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useCallback, useMemo } from 'react';

import { useTranslation } from 'next-i18next';

import { z } from 'zod';

import {
  isValidHuggingFaceToken,
  isValidKubernetesSecretName,
} from '@/utils/app/huggingface-secret';

import { HuggingFaceTokenData } from '@/types/secrets';

import { DrawerForm } from '@/components/shared/DrawerForm';
import { HuggingFaceTokenSelector } from '@/components/shared/HuggingFaceTokenSelector';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onApply: (data: HuggingFaceTokenData) => void;
  existingTokens?: { id: string; name: string }[];
}

export const HuggingFaceTokenDrawer = ({
  isOpen,
  onClose,
  onApply,
  existingTokens = [],
}: Props) => {
  const { t } = useTranslation('models');

  const validationSchema = useMemo(
    () =>
      z
        .object({
          selectedToken: z.string().optional(),
          name: z.string().optional(),
          token: z.string().optional(),
        })
        .superRefine((data, ctx) => {
          if (data.selectedToken && data.selectedToken.trim() !== '') {
            return;
          }

          const hasName = data.name && data.name.trim() !== '';
          const hasToken = data.token && data.token.trim() !== '';

          if (!hasName && !hasToken) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: t(
                'huggingFaceTokenDrawer.validation.selectTokenOrProvideNameAndToken',
              ),
              path: ['name'],
            });
          } else if (!hasName) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: t('huggingFaceTokenDrawer.validation.nameRequired'),
              path: ['name'],
            });
          } else if (hasName && !isValidKubernetesSecretName(data.name!)) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: t('huggingFaceTokenDrawer.validation.invalidSecretName'),
              path: ['name'],
            });
          } else if (hasName && data.name!.trim().length > 253) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: t('huggingFaceTokenDrawer.validation.nameTooLong'),
              path: ['name'],
            });
          } else if (!hasToken) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: t('huggingFaceTokenDrawer.validation.tokenRequired'),
              path: ['token'],
            });
          } else if (hasToken && !isValidHuggingFaceToken(data.token!)) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: t(
                'huggingFaceTokenDrawer.validation.invalidTokenFormat',
              ),
              path: ['token'],
            });
          }
        }),
    [t],
  );

  const handleFormSuccess = useCallback(
    (data: HuggingFaceTokenData) => {
      onApply(data);
      onClose();
    },
    [onApply, onClose],
  );

  const handleCancel = useCallback(() => {
    onClose();
  }, [onClose]);

  return (
    <DrawerForm<HuggingFaceTokenData>
      isOpen={isOpen}
      onCancel={handleCancel}
      onFormSuccess={handleFormSuccess}
      title={t('huggingFaceTokenDrawer.title')}
      cancelText={t('huggingFaceTokenDrawer.actions.cancel')}
      confirmText={t('huggingFaceTokenDrawer.actions.apply')}
      validationSchema={validationSchema}
      defaultValues={{
        selectedToken: '',
        name: '',
        token: '',
      }}
      renderFields={(form) => (
        <HuggingFaceTokenSelector form={form} existingTokens={existingTokens} />
      )}
    />
  );
};

export default HuggingFaceTokenDrawer;
