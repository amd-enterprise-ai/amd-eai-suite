// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Switch, SwitchProps } from '@heroui/react';
import { FieldValues, Path, PathValue, UseFormReturn } from 'react-hook-form';

interface Props<T extends FieldValues>
  extends Omit<SwitchProps, 'form' | 'name' | 'isSelected' | 'onValueChange'> {
  form: UseFormReturn<T>;
  name: Path<T>;
}

export const FormSwitch = <T extends FieldValues>({
  form,
  name,
  ...props
}: Props<T>): React.ReactElement => {
  const { onChange: _, ...registration } = form.register(name);
  const value = form.watch(name) as boolean;

  return (
    <Switch
      {...props}
      {...registration}
      isSelected={!!value}
      onValueChange={(next) =>
        form.setValue(name, next as PathValue<T, Path<T>>, {
          shouldValidate: true,
        })
      }
    />
  );
};

FormSwitch.displayName = 'FormSwitch';

export default FormSwitch;
