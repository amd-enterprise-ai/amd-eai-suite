// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Drawer,
  DrawerBody,
  DrawerContent,
  DrawerFooter,
  DrawerHeader,
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
import { BACKDROP, CLASSES, MOTION_PROPS } from './constants';

import { ZodType } from 'zod';

interface Props<T extends FieldValues> {
  isOpen?: boolean;
  isActioning?: boolean;
  isDisabled?: boolean;
  hideCloseButton?: boolean;

  title: string;
  confirmText: string;
  cancelText: string;

  onOpenChange?: () => void;
  onCancel?: () => void;
  onFormSuccess?: (data: T) => void;
  onFormFailure?: (errors: FieldErrors<T>, data: T) => void;
  renderFields: (form: UseFormReturn<T>) => React.ReactNode;
  defaultValues?: DefaultValues<T>;
  validationSchema: ZodType<T>;
  resolver?: (schema: ZodType<T>) => Resolver<T>;
}

export const DrawerForm = <T extends FieldValues>({
  isOpen,
  isActioning,
  isDisabled,
  hideCloseButton,
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
    <Drawer
      isOpen={isOpen}
      onOpenChange={onOpenChange}
      onClose={() => {
        if (onCancel) {
          onCancel();
        }
      }}
      motionProps={MOTION_PROPS}
      backdrop={BACKDROP}
      closeButton={<CloseButton />}
      hideCloseButton={
        hideCloseButton !== undefined ? hideCloseButton : isActioning
      }
      isDismissable={
        hideCloseButton !== undefined ? !hideCloseButton : !isActioning
      }
      classNames={CLASSES}
    >
      <DrawerContent>
        <DrawerHeader>{title}</DrawerHeader>
        <DrawerBody className="w-full">
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
        </DrawerBody>
        <DrawerFooter>
          <ActionButton
            tertiary
            aria-label={cancelText}
            type="reset"
            onPress={handleCancel}
          >
            {cancelText}
          </ActionButton>
          <ActionButton
            primary
            aria-label={confirmText}
            isLoading={isActioning}
            isDisabled={isDisabled}
            type="submit"
            onPress={handleFormSubmit}
          >
            {confirmText}
          </ActionButton>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  );
};

export default DrawerForm;
