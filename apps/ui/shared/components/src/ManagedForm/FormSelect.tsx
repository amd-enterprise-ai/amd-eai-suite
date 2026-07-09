// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Select, SelectProps } from '@amdenterpriseai/components';

import { cn } from '@heroui/react';
import { FieldValues, Path, UseFormReturn } from 'react-hook-form';

interface Props<T extends FieldValues>
  extends Omit<SelectProps, 'form' | 'name'> {
  form: UseFormReturn<T>;
  name: Path<T>;
}

export const FormSelect = <T extends FieldValues>({
  form,
  name,
  className,
  children,
  defaultSelectedKeys,
  startContent,
  ...props
}: Props<T>): React.ReactElement => {
  const registration = form.register(name);
  const errorMessage = form.formState.errors[name as string]?.message as string;
  const watchedValue = form.watch(name);
  const isSingle = !props.selectionMode || props.selectionMode === 'single';
  const selectedKeys =
    watchedValue != null
      ? isSingle
        ? [String(watchedValue)]
        : String(watchedValue).split(',').filter(Boolean)
      : [];

  return (
    <Select
      labelPlacement="outside"
      variant="bordered"
      {...props}
      {...registration}
      defaultSelectedKeys={defaultSelectedKeys}
      selectedKeys={selectedKeys}
      className={cn(className, {
        'text-opacity-disabled': props?.isDisabled,
        'text-foreground': props?.isDisabled,
      })}
      isInvalid={!!errorMessage}
      errorMessage={errorMessage}
      startContent={startContent}
    >
      {children}
    </Select>
  );
};

FormSelect.displayName = 'FormSelect';

export default FormSelect;
