// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Input, InputProps } from '@heroui/react';
import { cn } from '@heroui/react';
import { ComponentType, useCallback, useEffect } from 'react';
import { FieldValues, Path, UseFormReturn } from 'react-hook-form';

interface Props<T extends FieldValues>
  extends Omit<InputProps, 'form' | 'name'> {
  icon?: ComponentType<any>;
  form: UseFormReturn<T>;
  name: Path<T>;
}

export const FormInput = <T extends FieldValues>({
  form,
  icon: Icon,
  name,
  className,
  ...props
}: Props<T>): React.ReactElement => {
  const registration = form.register(name as Path<T>);
  const errorMessage = form.formState.errors[name as string]?.message as string;

  // remove form value when the component unmounts
  const unregisterField = useCallback(() => {
    if (!!name) {
      form.unregister(name, {
        keepValue: false,
      });
    }
  }, [form, name]);

  useEffect(() => {
    return unregisterField;
  }, [unregisterField]);

  return (
    <Input
      labelPlacement="outside"
      variant="bordered"
      {...props}
      {...registration}
      className={cn(className, {
        'text-opacity-disabled': props?.isReadOnly,
        'text-foreground': props?.isReadOnly,
      })}
      isInvalid={!!errorMessage}
      errorMessage={errorMessage}
      startContent={
        Icon ? (
          <Icon
            className={cn({
              'stroke-danger': !!errorMessage,
              'stroke-neutral-500': !errorMessage,
            })}
          />
        ) : null
      }
    />
  );
};

FormInput.displayName = 'FormInput';

export default FormInput;
