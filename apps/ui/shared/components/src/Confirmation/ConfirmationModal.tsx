// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  ModalPrimitive,
  ModalPrimitiveBody,
  ModalPrimitiveContent,
  ModalPrimitiveFooter,
  ModalPrimitiveHeader,
} from '../Modal/ModalPrimitive';
import { FC, ReactNode } from 'react';

import { Trans, useTranslation } from 'next-i18next';
import { ActionButton } from '../Buttons';

interface Props {
  description: string | ReactNode;
  title: string;
  confirmationButtonColor?:
    | 'default'
    | 'primary'
    | 'secondary'
    | 'success'
    | 'warning'
    | 'danger';
  isOpen: boolean;
  loading: boolean;
  confirmationButtonText?: string;
  onConfirm: () => void;
  onClose?: () => void;
  onOpen?: () => void;
}

export const ConfirmationModal: FC<Props> = ({
  title,
  description,
  confirmationButtonColor,
  isOpen,
  loading,
  onConfirm,
  onClose,
  confirmationButtonText,
}) => {
  const { t } = useTranslation('common');
  return (
    <div className="flex items-center justify-center text-default-900 rounded-lg">
      <ModalPrimitive
        data-testid="confirmation-modal"
        hideCloseButton
        isDismissable={!loading}
        onClose={onClose}
        isOpen={isOpen}
      >
        <ModalPrimitiveContent>
          <ModalPrimitiveHeader className="flex flex-col gap-1">
            {title}
          </ModalPrimitiveHeader>
          <ModalPrimitiveBody className="dark:text-default-500 text-default-600">
            <Trans parent="p">{description}</Trans>
          </ModalPrimitiveBody>
          <ModalPrimitiveFooter>
            <ActionButton
              tertiary
              aria-label={t('actions.close.title') || ''}
              isDisabled={loading}
              onPress={onClose}
            >
              {t('actions.close.title')}
            </ActionButton>
            <ActionButton
              primary
              aria-label={
                confirmationButtonText || t('actions.confirm.title') || ''
              }
              data-testid="confirm-button"
              isLoading={loading}
              color={confirmationButtonColor}
              onPress={onConfirm}
            >
              {confirmationButtonText || t('actions.confirm.title')}
            </ActionButton>
          </ModalPrimitiveFooter>
        </ModalPrimitiveContent>
      </ModalPrimitive>
    </div>
  );
};
