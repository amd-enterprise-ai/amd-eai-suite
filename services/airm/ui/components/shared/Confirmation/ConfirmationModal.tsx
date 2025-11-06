// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Modal,
  ModalBody,
  ModalContent,
  ModalFooter,
  ModalHeader,
} from '@heroui/react';
import { FC, ReactNode } from 'react';

import { useTranslation } from 'next-i18next';
import { ActionButton } from '@/components/shared/Buttons';

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
  const { t } = useTranslation();
  return (
    <div className="flex items-center justify-center text-default-900 rounded-lg">
      <Modal
        data-testid="confirmation-modal"
        hideCloseButton
        isDismissable={!loading}
        onClose={onClose}
        isOpen={isOpen}
      >
        <ModalContent>
          <>
            <ModalHeader className="flex flex-col gap-1">{title}</ModalHeader>
            <ModalBody className="dark:text-default-500 text-default-600">
              {description}
            </ModalBody>
            <ModalFooter>
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
            </ModalFooter>
          </>
        </ModalContent>
      </Modal>
    </div>
  );
};
