// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  ModalBody,
  ModalContent,
  ModalFooter,
  ModalHeader,
  Modal as NextModal,
} from '@heroui/react';
import React from 'react';
import { CloseButton } from '@/components/shared/Buttons';

interface ModalProps {
  children: React.ReactNode;
  onClose: () => void;
  footer?: React.ReactNode;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl';
  title?: string;
  subTitle?: string;
  isDismissible?: boolean;
}

export const Modal: React.FC<ModalProps> = ({
  children,
  footer,
  onClose,
  size,
  title,
  subTitle,
  isDismissible,
}) => {
  return (
    <NextModal
      isOpen={true}
      onOpenChange={onClose}
      isDismissable={isDismissible}
      size={size || 'xl'}
      closeButton={<CloseButton />}
      classNames={{
        base: 'overflow-y-auto overflow-x-hidden',
        header: 'border-b-1 border-default-200 w-full pr-[64px]',
        body: 'py-6',
        closeButton: 'top-2.5 right-2.5',
        footer: 'justify-center w-full',
      }}
    >
      <ModalContent className="max-h-[95vh] sm:my-1">
        <ModalHeader>
          <div className="flex flex-col gap-1">
            <h2>{title || ''}</h2>
            {subTitle ? (
              <p className="dark:text-default-500 text-default-600 font-medium">
                {subTitle}
              </p>
            ) : null}
          </div>
        </ModalHeader>
        <ModalBody>{children}</ModalBody>
        {footer ? <ModalFooter>{footer}</ModalFooter> : null}
      </ModalContent>
    </NextModal>
  );
};
