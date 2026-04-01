// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useEffect, useState } from 'react';

import { useTranslation } from 'next-i18next';

import { Model } from '@amdenterpriseai/types';

import { ConfirmationModal } from '@amdenterpriseai/components';

interface DeleteModelModalProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  onConfirmAction: ({ id }: { id: string }) => void;
  model: Model | undefined;
}

export default function DeleteModelModal({
  isOpen,
  onOpenChange,
  onConfirmAction,
  model,
}: DeleteModelModalProps) {
  const { t } = useTranslation('models', { keyPrefix: 'customModels' });
  const [isLoading, setIsLoading] = useState(false);

  // Reset loading state when modal is closed
  useEffect(() => {
    if (!isOpen) {
      setIsLoading(false);
    }
  }, [isOpen]);

  if (!model) return null;

  const handleConfirm = () => {
    if (isLoading) return; // Prevent multiple clicks

    setIsLoading(true);
    onConfirmAction({ id: model.id });
    onOpenChange(false);
  };

  const handleClose = () => {
    setIsLoading(false);
    onOpenChange(false);
  };

  return (
    <ConfirmationModal
      confirmationButtonColor="danger"
      description={t('list.actions.delete.confirmation.description', {
        name: model.name || '',
      })}
      title={t('list.actions.delete.confirmation.title')}
      isOpen={isOpen}
      loading={isLoading}
      onConfirm={handleConfirm}
      onClose={handleClose}
    />
  );
}
