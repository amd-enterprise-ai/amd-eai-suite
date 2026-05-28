// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useTranslation } from 'next-i18next';

import { Model } from '@/types/models';

import { ConfirmationModal } from '@amdenterpriseai/components';

interface DeleteModelModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirmAction: ({ name }: { name: string }) => void;
  model: Model | undefined;
  hasActiveDeployments: boolean;
  loading: boolean;
}

export default function DeleteModelModal({
  isOpen,
  onClose,
  onConfirmAction,
  model,
  hasActiveDeployments,
  loading,
}: DeleteModelModalProps) {
  const { t } = useTranslation('models', { keyPrefix: 'customModels' });

  if (!model) return null;

  const handleConfirm = () => {
    if (loading || !model.resourceName) return;
    onConfirmAction({ name: model.resourceName });
  };

  const description = hasActiveDeployments
    ? t('list.actions.delete.confirmation.conflictDescription', {
        name: model.name || '',
      })
    : t('list.actions.delete.confirmation.description', {
        name: model.name || '',
      });

  return (
    <ConfirmationModal
      confirmationButtonColor="danger"
      description={description}
      title={t('list.actions.delete.confirmation.title')}
      isOpen={isOpen}
      loading={loading}
      onConfirm={handleConfirm}
      onClose={onClose}
    />
  );
}
