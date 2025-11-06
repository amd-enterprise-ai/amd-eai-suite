// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Slider, SliderProps, cn } from '@heroui/react';
import { useMemo } from 'react';
import { FieldValues, Path, UseFormReturn } from 'react-hook-form';

import { useBoundaryValidation } from '@/hooks/useBoundaryValidation';

interface Props<T extends FieldValues>
  extends Omit<SliderProps, 'form' | 'name' | 'onChange' | 'value'> {
  form: UseFormReturn<T>;
  name: Path<T>;
  description?: string;
}

export const FormSlider = <T extends FieldValues>({
  form,
  name,
  className,
  description = '',
  color,
  ...props
}: Props<T>) => {
  const { currentValue, updateFormValue } = useBoundaryValidation(
    form,
    name,
    props.minValue,
    props.maxValue,
  );

  const { onChange: _, ...registration } = form.register(name, {
    setValueAs: (value) =>
      value === '' || value === null || value === undefined
        ? undefined
        : Number(value),
  });
  const errorMessage =
    typeof form.formState.errors[name]?.message === 'string'
      ? form.formState.errors[name]?.message
      : undefined;

  const safeCurrentValue = useMemo(() => {
    if (currentValue !== undefined && currentValue !== null)
      return currentValue;

    if (props.defaultValue !== undefined) return props.defaultValue;

    return props.minValue ?? 0;
  }, [currentValue, props.defaultValue, props.minValue]);

  return (
    <div className={cn('flex flex-col gap-1', className)}>
      <Slider
        {...props}
        {...registration}
        value={safeCurrentValue}
        isInvalid={!!errorMessage}
        errorMessage={errorMessage}
        onChange={updateFormValue}
        color={!errorMessage ? color : 'danger'}
        classNames={{
          mark: 'text-tiny',
        }}
      />
      {(!!errorMessage || description) && (
        <div
          className={cn('text-tiny p-1 relative flex flex-col gap-1.5', {
            'text-foreground-400': !errorMessage,
            'text-danger': !!errorMessage,
          })}
        >
          {errorMessage || description}
        </div>
      )}
    </div>
  );
};

FormSlider.displayName = 'FormSlider';

export default FormSlider;
