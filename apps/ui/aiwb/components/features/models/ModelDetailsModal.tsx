// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Button, Chip, Modal } from '@amdenterpriseai/components';

import { useTranslation } from 'next-i18next';

import { AIM_MODEL_NAME_LABEL, AIMModel, AIMStatus } from '@/types/aims';
import { resolveBaseModelSource } from '@/lib/app/aims';

import AIMConditionsList from '@/components/shared/AIMConditionsList';

interface Props {
  model: AIMModel | undefined;
  onOpenChange: (isOpen: boolean) => void;
  isOpen: boolean;
}

const ModelDetailsModal = ({ model, isOpen, onOpenChange }: Props) => {
  const { t } = useTranslation('models', { keyPrefix: 'customModels' });

  const handleClose = () => onOpenChange(false);

  const name =
    model?.metadata.labels?.[AIM_MODEL_NAME_LABEL] || model?.metadata.name;
  const canonicalName = model
    ? resolveBaseModelSource(model)?.modelId
    : undefined;
  const conditions = model?.status?.conditions ?? [];

  return (
    <>
      {isOpen && (
        <Modal
          onClose={handleClose}
          title={
            t('list.actions.details.modal.title', {
              modelName: name ?? 'Model',
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
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="font-semibold text-default-600">
                    {t('list.actions.details.modal.fields.name')}
                  </p>
                  <p>{name}</p>
                </div>
                {canonicalName && (
                  <div>
                    <p className="font-semibold text-default-600">
                      {t('list.actions.details.modal.fields.baseModel')}
                    </p>
                    <p className="font-mono">{canonicalName}</p>
                  </div>
                )}
                <div>
                  <p className="font-semibold text-default-600">
                    {t('list.actions.details.modal.fields.resourceName')}
                  </p>
                  <p className="font-mono text-xs">{model.metadata.name}</p>
                </div>
                {model.status?.status && (
                  <div>
                    <p className="font-semibold text-default-600">
                      {t('list.actions.details.modal.fields.status')}
                    </p>
                    <Chip
                      size="sm"
                      color={
                        model.status.status === AIMStatus.READY
                          ? 'success'
                          : model.status.status === AIMStatus.DEGRADED ||
                              model.status.status === AIMStatus.FAILED
                            ? 'danger'
                            : 'warning'
                      }
                      variant="flat"
                    >
                      {model.status.status}
                    </Chip>
                  </div>
                )}
              </div>

              {conditions.length > 0 && (
                <div>
                  <p className="font-semibold text-default-600 mb-2">
                    {t('list.actions.details.modal.fields.conditions')}
                  </p>
                  <AIMConditionsList conditions={conditions} />
                </div>
              )}
            </div>
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
