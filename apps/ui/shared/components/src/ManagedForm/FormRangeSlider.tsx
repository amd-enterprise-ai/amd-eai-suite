// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Slider, SliderProps } from '@amdenterpriseai/components';
import { useEffect } from 'react';
import { FieldValues, Path, PathValue, UseFormReturn } from 'react-hook-form';

interface Props<T extends FieldValues>
  extends Omit<SliderProps, 'form' | 'name' | 'onChange' | 'value'> {
  form: UseFormReturn<T>;
  /** Form field name for the lower bound of the range. */
  minName: Path<T>;
  /** Form field name for the upper bound of the range. */
  maxName: Path<T>;
}

/**
 * Range slider that controls two separate form fields (min and max).
 * Registers both fields on mount and unregisters them on unmount, ensuring
 * correct cleanup when the slider is conditionally removed from a form with
 * shouldUnregister: true (as ManagedForm uses).
 */
export const FormRangeSlider = <T extends FieldValues>({
  form,
  minName,
  maxName,
  ...props
}: Props<T>) => {
  useEffect(() => {
    form.register(minName);
    form.register(maxName);
    return () => {
      form.unregister(minName);
      form.unregister(maxName);
    };
  }, [form, minName, maxName]);

  const minValue = form.watch(minName) as number | undefined;
  const maxValue = form.watch(maxName) as number | undefined;

  const sliderValue: [number, number] = [
    minValue ?? props.minValue ?? 0,
    maxValue ?? props.maxValue ?? 100,
  ];

  return (
    <Slider
      {...props}
      value={sliderValue}
      onChange={(value) => {
        if (!Array.isArray(value)) return;
        const [min, max] = value as [number, number];
        form.setValue(minName, min as PathValue<T, Path<T>>, {
          shouldValidate: true,
          shouldDirty: true,
        });
        form.setValue(maxName, max as PathValue<T, Path<T>>, {
          shouldValidate: true,
          shouldDirty: true,
        });
      }}
    />
  );
};

FormRangeSlider.displayName = 'FormRangeSlider';

export default FormRangeSlider;
