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
import { useCallback, useRef } from 'react';
import {
  DefaultValues,
  FieldErrors,
  FieldValues,
  Resolver,
  UseFormReturn,
} from 'react-hook-form';
import { ActionButton, CloseButton } from '@/components/shared/Buttons';
import ManagedForm from '../ManagedForm/ManagedForm';

import { ZodType } from 'zod';

interface Props<T extends FieldValues> {
  isOpen?: boolean;
  isActioning?: boolean;

  title: string;
  confirmText: string;
  cancelText: string;

  children?: React.ReactNode;
  onOpenChange?: () => void;
  onCancel?: () => void;
  onFormSuccess?: (data: T) => void;
  onFormFailure?: (errors: FieldErrors<T>, data: T) => void;
  renderFields: (form: UseFormReturn<T>) => React.ReactNode;
  defaultValues?: DefaultValues<T>;
  validationSchema: ZodType<T>;
  resolver?: (schema: ZodType<T>) => Resolver<T>;
}

export const ModalForm = <T extends FieldValues>({
  isOpen,
  isActioning,
  onOpenChange,
  cancelText,
  confirmText,
  title,
  onCancel,
  onFormSuccess,
  onFormFailure,
  defaultValues,
  validationSchema,
  resolver,
  renderFields,
}: Props<T>) => {
  const formRef = useRef<HTMLFormElement>(null);

  const handleFormSubmit = useCallback(() => {
    formRef?.current?.requestSubmit();
  }, [formRef]);

  const handleCancel = useCallback(() => {
    if (onCancel) {
      onCancel();
    } else {
      onOpenChange?.();
    }
  }, [onCancel, onOpenChange]);

  const handleFormSuccess = useCallback(
    (data: T) => {
      if (onFormSuccess) {
        onFormSuccess(data as T);
      }
    },
    [onFormSuccess],
  );

  const handleFormFailure = useCallback(
    (errors: FieldErrors<T>, data: T) => {
      if (onFormFailure) {
        onFormFailure(errors, data);
      }
    },
    [onFormFailure],
  );

  return (
    <Modal
      isOpen={isOpen}
      onOpenChange={onOpenChange}
      classNames={{
        base: 'overflow-y-auto overflow-x-hidden',
        header: 'border-b-1 border-default-200 w-full pr-[64px]',
        body: 'py-6',
        closeButton: 'top-2.5 right-2.5',
        footer: 'justify-center w-full',
      }}
      onClose={() => {
        if (onCancel) {
          onCancel();
        }
      }}
      closeButton={<CloseButton />}
      hideCloseButton={isActioning}
      isDismissable={!isActioning}
    >
      <ModalContent>
        <ModalHeader>{title}</ModalHeader>
        <ModalBody className="w-full">
          <ManagedForm<T>
            isActioning={isActioning}
            onFormSuccess={handleFormSuccess}
            onFormFailure={handleFormFailure}
            validationSchema={validationSchema}
            resolver={resolver}
            renderFields={renderFields}
            defaultValues={defaultValues}
            formRef={formRef}
          />
        </ModalBody>
        <ModalFooter>
          <ActionButton
            secondary
            data-testid="modal-cancel"
            aria-label={cancelText}
            type="reset"
            onPress={handleCancel}
          >
            {cancelText}
          </ActionButton>
          <ActionButton
            primary
            data-testid="modal-confirm"
            aria-label={confirmText}
            isLoading={isActioning}
            type="submit"
            onPress={handleFormSubmit}
          >
            {confirmText}
          </ActionButton>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default ModalForm;
