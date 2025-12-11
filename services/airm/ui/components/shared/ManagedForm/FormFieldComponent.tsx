// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { Button, Input } from '@heroui/react';
import { cn } from '@heroui/react';
import {
  FieldValues,
  Path,
  UseFormRegister,
  UseFormReturn,
} from 'react-hook-form';

import { FormField } from '@/types/forms/forms';

interface Props<T extends FieldValues> {
  formField: FormField<T>;
  isDisabled?: boolean;
  errorMessage?: string;
  register: UseFormRegister<T> | null;
  form?: UseFormReturn<T>;
  defaultValue?: unknown;
  className?: string;
}

export const FormFieldComponent = <T extends FieldValues>({
  defaultValue,
  formField,
  isDisabled,
  errorMessage,
  className,
  register,
  form,
}: Props<T>) => {
  const Component = (formField.component as React.ElementType) || Input;

  const FormField = (
    <Component
      {...formField?.props}
      {...(register ? register(formField.name as Path<T>) : {})}
      className={cn(className, {
        'text-opacity-disabled': formField.isReadOnly,
        'text-foreground': formField.isReadOnly,
      })}
      form={form}
      name={formField.name}
      isDisabled={isDisabled}
      isRequired={formField.isRequired}
      label={formField.label}
      labelPlacement="outside"
      isReadOnly={formField.isReadOnly}
      isInvalid={!!errorMessage}
      placeholder={formField.placeholder}
      errorMessage={errorMessage}
      description={formField.description}
      variant="bordered"
      defaultValue={defaultValue}
      startContent={
        formField?.icon ? (
          <formField.icon
            className={cn({
              'stroke-danger': !!errorMessage,
              'stroke-neutral-500': !!errorMessage,
            })}
          />
        ) : null
      }
    />
  );
  return formField.secondaryAction ? (
    <div className="relative">
      {formField.secondaryAction ? (
        <div className="absolute top-[-0.6rem] right-2">
          <Button
            size="sm"
            variant="light"
            color="primary"
            onPress={formField.secondaryAction.callback}
          >
            {formField.secondaryAction.label}
          </Button>
        </div>
      ) : null}
      {FormField}
    </div>
  ) : (
    FormField
  );
};

export default FormFieldComponent;
