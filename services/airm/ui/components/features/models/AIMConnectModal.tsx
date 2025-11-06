// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Input, Snippet } from '@heroui/react';
import { IconCopy } from '@tabler/icons-react';
import React from 'react';

import { useTranslation } from 'next-i18next';

import { Aim } from '@/types/aims';

import { Modal } from '@/components/shared/Modal/Modal';
import { ActionButton } from '@/components/shared/Buttons';

interface Props {
  onOpenChange: (isOpen: boolean) => void;
  onConfirmAction: (aim: Aim) => void;
  isOpen: boolean;
  aim: Aim | undefined;
}

const AIMConnectModal = ({
  onOpenChange,
  onConfirmAction,
  isOpen,
  aim,
}: Props) => {
  const { t } = useTranslation('models', { keyPrefix: 'aimCatalog' });
  const { t: tc } = useTranslation('common');

  const handleClose = () => {
    if (onOpenChange) {
      onOpenChange(false);
    }
  };

  const handleConfirm = () => {
    if (aim && onConfirmAction) {
      onConfirmAction(aim);
      onOpenChange(false);
    }
  };

  const workload = aim?.workload;

  const externalUrl = workload?.output?.externalHost
    ? `${workload.output.externalHost}/v1/chat/completions`
    : '';

  const internalUrl = workload?.output?.internalHost
    ? `http://${workload.output.internalHost}/v1/chat/completions`
    : '';

  const codeBlock = `curl -X POST "${externalUrl}" \\
  -H "Authorization: Bearer UPDATE_YOUR_API_KEY_HERE" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "${aim?.canonicalName || ''}",
    "messages": [
      {
        "content": "Hello",
        "role": "user"
      }
    ],
    "stream": false
  }'`;

  return (
    <>
      {isOpen && (
        <Modal
          size="xl"
          title={t('actions.connect.modal.title') as string}
          onClose={handleClose}
          footer={
            <>
              <ActionButton secondary onPress={handleClose}>
                {tc('actions.close.title')}
              </ActionButton>
              <ActionButton primary onPress={handleConfirm}>
                {t('actions.connect.modal.openChat')}
              </ActionButton>
            </>
          }
        >
          <div className="space-y-4">
            {externalUrl ? (
              <Input
                value={externalUrl}
                labelPlacement="outside"
                label={t('actions.connect.modal.externalUrl')}
                readOnly
                className="w-full mb-6 pb-6"
                aria-label={t('actions.connect.modal.externalUrl')}
              />
            ) : null}

            <Input
              value={internalUrl}
              readOnly
              labelPlacement="outside"
              label={t('actions.connect.modal.internalUrl')}
              className="w-full mb-4"
              aria-label={t('actions.connect.modal.internalUrl')}
            />

            <div>
              <label className="block text-sm font-medium text-foreground-500 mb-3">
                {t('actions.connect.modal.codeExample')}
              </label>
              <Snippet
                classNames={{
                  base: 'w-full relative',
                  pre: 'whitespace-pre-wrap font-mono',
                  copyButton: 'absolute top-2 right-2',
                }}
                copyIcon={<IconCopy />}
                aria-label={t('actions.connect.modal.codeExample')}
                symbol=""
              >
                {codeBlock}
              </Snippet>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
};

export default AIMConnectModal;
