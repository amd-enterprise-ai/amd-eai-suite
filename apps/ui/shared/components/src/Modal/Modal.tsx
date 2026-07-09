// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  ModalPrimitive,
  ModalPrimitiveBody,
  ModalPrimitiveContent,
  ModalPrimitiveFooter,
  ModalPrimitiveHeader,
} from './ModalPrimitive';
import React from 'react';
import { CloseButton } from '../Buttons';

interface ModalProps {
  children: React.ReactNode;
  onClose: () => void;
  footer?: React.ReactNode;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl' | '4xl' | '5xl';
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
    <ModalPrimitive
      isOpen={true}
      onOpenChange={onClose}
      isDismissable={isDismissible}
      size={size || 'xl'}
      closeButton={<CloseButton />}
      classNames={{
        base: 'overflow-y-auto overflow-x-hidden',
        header: 'border-b-1 border-default-200 w-full pr-[64px]',
        body: 'pt-6 pb-2',
        closeButton: 'top-2.5 right-2.5',
        footer: 'justify-center w-full',
      }}
    >
      <ModalPrimitiveContent className="max-h-[95vh] sm:my-1">
        <ModalPrimitiveHeader>
          <div className="flex flex-col gap-1">
            <h2>{title || ''}</h2>
            {subTitle ? (
              <p className="dark:text-default-500 text-default-600 font-medium">
                {subTitle}
              </p>
            ) : null}
          </div>
        </ModalPrimitiveHeader>
        <ModalPrimitiveBody>{children}</ModalPrimitiveBody>
        {footer ? <ModalPrimitiveFooter>{footer}</ModalPrimitiveFooter> : null}
      </ModalPrimitiveContent>
    </ModalPrimitive>
  );
};
