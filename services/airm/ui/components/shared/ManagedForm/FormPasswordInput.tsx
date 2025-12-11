// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React, { ComponentType, useCallback, useEffect } from 'react';

import { InputProps } from '@heroui/react';
import { cn } from '@heroui/react';
import type { FieldValues, Path, UseFormReturn } from 'react-hook-form';

import { PasswordInput } from '../Input/PasswordInput';

interface Props<T extends FieldValues>
  extends Omit<InputProps, 'form' | 'name' | 'type'> {
  icon?: ComponentType<any>;
  form: UseFormReturn<T>;
  name: Path<T>;
}

export const FormPasswordInput = <T extends FieldValues>({
  form,
  icon,
  name,
  className,
  ...props
}: Props<T>): React.ReactElement => {
  const registration = form.register(name as Path<T>);
  const errorMessage = form.formState.errors[name as string]?.message as string;

  // remove form value when the component unmounts
  const unregisterField = useCallback(() => {
    if (name) {
      form.unregister(name, {
        keepValue: false,
      });
    }
  }, [form, name]);

  useEffect(() => {
    return unregisterField;
  }, [unregisterField]);

  return (
    <PasswordInput
      {...props}
      {...registration}
      icon={icon}
      className={cn(className, {
        'text-opacity-disabled': props?.isReadOnly,
        'text-foreground': props?.isReadOnly,
      })}
      isInvalid={!!errorMessage}
      errorMessage={errorMessage}
    />
  );
};

FormPasswordInput.displayName = 'FormPasswordInput';

export default FormPasswordInput;
