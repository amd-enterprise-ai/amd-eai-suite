// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Button } from '@heroui/react';

import { useTranslation } from 'next-i18next';

import { Model } from '@/types/models';

import { Modal } from '@/components/shared/Modal/Modal';

interface Props {
  model: Model | undefined;
  onOpenChange: (isOpen: boolean) => void;
  isOpen: boolean;
}

const ModelDetailsModal = ({ model, isOpen, onOpenChange }: Props) => {
  const { t } = useTranslation('models', { keyPrefix: 'customModels' });

  const handleClose = () => {
    if (onOpenChange) {
      onOpenChange(false);
    }
  };

  return (
    <>
      {isOpen && (
        <Modal
          onClose={handleClose}
          title={
            t('list.actions.details.modal.title', {
              modelName: model ? model.name : 'Model',
            }) as string
          }
          size="xl"
          footer={
            <Button color="default" onPress={handleClose}>
              {t('list.actions.details.modal.close')}
            </Button>
          }
        >
          {model ? (
            Object.entries(model).map(([key, value]) => (
              <div key={key} className="mb-4">
                <div className="mb-0 font-semibold">{key}</div>
                <div className="dark:text-default-500 text-default-600">
                  {typeof value === 'object'
                    ? JSON.stringify(value)
                    : String(value)}
                </div>
              </div>
            ))
          ) : (
            <div className="p-4 text-default-600">
              {t('list.actions.details.modal.modelNotFound')}
            </div>
          )}
        </Modal>
      )}
    </>
  );
};

export default ModelDetailsModal;
