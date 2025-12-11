// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Select, SelectProps } from '@heroui/react';
import { cn } from '@heroui/react';
import { ComponentType, useCallback, useEffect } from 'react';
import { FieldValues, Path, UseFormReturn } from 'react-hook-form';

interface Props<T extends FieldValues>
  extends Omit<SelectProps, 'form' | 'name'> {
  icon?: ComponentType<{ className?: string }>;
  form: UseFormReturn<T>;
  name: Path<T>;
}

export const FormSelect = <T extends FieldValues>({
  form,
  icon: Icon,
  name,
  className,
  children,
  ...props
}: Props<T>): React.ReactElement => {
  const registration = form.register(name);
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
    <Select
      labelPlacement="outside"
      variant="bordered"
      {...props}
      {...registration}
      className={cn(className, {
        'text-opacity-disabled': props?.isDisabled,
        'text-foreground': props?.isDisabled,
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
    >
      {children}
    </Select>
  );
};

FormSelect.displayName = 'FormSelect';

export default FormSelect;
