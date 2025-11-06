// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { NumberInput, NumberInputProps } from '@heroui/react';
import { cn } from '@heroui/react';
import { ComponentType, useCallback, useEffect } from 'react';
import { FieldValues, Path, PathValue, UseFormReturn } from 'react-hook-form';

interface Props<T extends FieldValues>
  extends Omit<NumberInputProps, 'form' | 'name'> {
  icon?: ComponentType<any>;
  form: UseFormReturn<T>;
  name: Path<T>;
}

export const FormNumberInput = <T extends FieldValues>({
  form,
  icon: Icon,
  name,
  className,
  ...props
}: Props<T>) => {
  const { onChange: _, ...registration } = form.register(name, {
    setValueAs: (value) => (!value ? undefined : Number(value)),
  });
  const errorMessage = form.formState.errors[name]?.message as string;

  // custom update handler to work with number instead of formatted string
  const updateFormValue = useCallback(
    (value: number): void => {
      if (isNaN(value))
        form.unregister(name, {
          keepValue: false,
        });
      else
        form.setValue(name, value as PathValue<T, Path<T>>, {
          shouldValidate: true,
        });
    },
    [form, name],
  );

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
    <NumberInput
      labelPlacement="outside"
      variant="bordered"
      {...props}
      {...registration}
      onValueChange={updateFormValue}
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

FormNumberInput.displayName = 'FormNumberInput';

export default FormNumberInput;
