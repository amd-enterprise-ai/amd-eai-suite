// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'next-i18next';
import { useMemo } from 'react';

import {
  HuggingFaceTokenSelector,
  type HuggingFaceTokenSelectorLabels,
} from '@amdenterpriseai/components';
import { SecretUseCase } from '@amdenterpriseai/types';
import { APIRequestError } from '@amdenterpriseai/utils/app';

import { createHuggingFaceSecretRequest } from '@/lib/app/huggingface-secret';
import { createProjectSecret, fetchProjectSecrets } from '@/lib/app/secrets';
import type { SecretResponseData } from '@/types/secrets';

export interface ProjectHuggingFaceTokenSelectorProps {
  namespace: string;
  value: string | null | undefined;
  onChange: (name: string) => void;
  isRequired?: boolean;
  isDisabled?: boolean;
  isInvalid?: boolean;
  errorMessage?: string;
}

/**
 * Project-scoped binding of the shared {@link HuggingFaceTokenSelector}.
 *
 * Fetches the namespace's HF token secrets, persists newly-created tokens
 * via the project secrets API, and surfaces translation strings from the
 * `models.huggingFaceTokenSelector` namespace. Consumers only need to
 * supply the active namespace and a value/onChange pair.
 */
export const ProjectHuggingFaceTokenSelector = ({
  namespace,
  value,
  onChange,
  isRequired,
  isDisabled,
  isInvalid,
  errorMessage,
}: ProjectHuggingFaceTokenSelectorProps) => {
  const { t } = useTranslation('models', {
    keyPrefix: 'huggingFaceTokenSelector',
  });
  const queryClient = useQueryClient();

  const { data: secrets } = useQuery<SecretResponseData[]>({
    queryKey: ['project', namespace, 'secrets'],
    queryFn: async () => {
      const response = await fetchProjectSecrets(namespace);
      return response.data;
    },
    enabled: !!namespace,
  });

  const tokens = useMemo(
    () =>
      (secrets ?? []).filter((s) => s.useCase === SecretUseCase.HUGGING_FACE),
    [secrets],
  );

  const createMutation = useMutation({
    mutationFn: async ({ name, token }: { name: string; token: string }) => {
      if (!namespace) {
        throw new APIRequestError(t('errors.missingNamespace'), 422);
      }
      const req = createHuggingFaceSecretRequest(name, token);
      const created = await createProjectSecret(namespace, req);
      const createdName = created.metadata?.name;
      if (!createdName) {
        throw new APIRequestError(t('errors.invalidSecretResponse'), 502);
      }
      return { name: createdName };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['project', namespace, 'secrets'],
      });
    },
  });

  const labels: HuggingFaceTokenSelectorLabels = {
    selectLabel: t('selectLabel'),
    selectPlaceholder: t('selectPlaceholder'),
    addNewItemLabel: t('addNew'),
    dialogTitle: t('dialog.title'),
    dialogNameLabel: t('dialog.nameLabel'),
    dialogNamePlaceholder: t('dialog.namePlaceholder'),
    dialogTokenLabel: t('dialog.tokenLabel'),
    dialogTokenPlaceholder: t('dialog.tokenPlaceholder'),
    dialogCancelLabel: t('dialog.cancel'),
    dialogSubmitLabel: t('dialog.submit'),
  };

  const tokenOptions = useMemo(
    () =>
      tokens.map((secret) => ({
        name: secret.metadata.name,
        displayName: secret.displayName,
      })),
    [tokens],
  );

  return (
    <HuggingFaceTokenSelector
      value={value}
      onChange={onChange}
      existingTokens={tokenOptions}
      onCreateToken={(input) => createMutation.mutateAsync(input)}
      labels={labels}
      isRequired={isRequired}
      isDisabled={isDisabled || !namespace}
      isInvalid={isInvalid}
      errorMessage={errorMessage}
      data-testid="project-hf-token-selector"
    />
  );
};

export default ProjectHuggingFaceTokenSelector;
