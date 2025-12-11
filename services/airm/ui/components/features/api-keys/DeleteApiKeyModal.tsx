// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useTranslation } from 'next-i18next';

import { ApiKey } from '@/types/api-keys';

import { ConfirmationModal } from '@/components/shared/Confirmation/ConfirmationModal';

interface DeleteApiKeyModalProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  onConfirmAction: (apiKey: ApiKey) => void;
  apiKey: ApiKey | undefined;
}

export default function DeleteApiKeyModal({
  isOpen,
  onOpenChange,
  onConfirmAction,
  apiKey,
}: DeleteApiKeyModalProps) {
  const { t } = useTranslation('api-keys');

  if (!apiKey) return null;

  const handleConfirm = () => {
    onConfirmAction(apiKey);
    onOpenChange(false);
  };

  return (
    <ConfirmationModal
      confirmationButtonColor="danger"
      description={t('list.actions.delete.confirmation.description', {
        name: apiKey.name || '',
      })}
      title={t('list.actions.delete.confirmation.title')}
      isOpen={isOpen}
      loading={false}
      onConfirm={handleConfirm}
      onClose={() => onOpenChange(false)}
    />
  );
}
