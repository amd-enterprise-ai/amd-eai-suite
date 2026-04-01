// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useCallback, useEffect, useRef, useState } from 'react';
import { FieldValues, Path, PathValue, UseFormReturn } from 'react-hook-form';

// Hook for watching form field values
export const useFormFieldValue = <T extends FieldValues>(
  form: UseFormReturn<T>,
  name: Path<T>,
) => {
  const [currentValue, setCurrentValue] = useState(() => form.getValues(name));
  const isUpdatingRef = useRef(false);

  const updateFormValue = useCallback(
    (value: number | number[]): void => {
      const numericValue = typeof value === 'number' ? value : value[0];

      isUpdatingRef.current = true;
      form.setValue(name, numericValue as PathValue<T, Path<T>>, {
        shouldValidate: true,
      });
      setCurrentValue(numericValue as PathValue<T, Path<T>>);

      // Reset flag after update
      queueMicrotask(() => {
        isUpdatingRef.current = false;
      });
    },
    [form, name],
  );

  useEffect(() => {
    const subscription = form.watch(() => {
      if (!isUpdatingRef.current) {
        const rawValue = form.getValues(name);
        setCurrentValue(rawValue);
      }
    });
    return () => subscription.unsubscribe();
  }, [form, name]);

  return { currentValue, updateFormValue, isUpdatingRef };
};
