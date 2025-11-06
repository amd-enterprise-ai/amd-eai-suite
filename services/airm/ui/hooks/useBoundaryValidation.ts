// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useEffect, useRef } from 'react';
import { FieldValues, Path, UseFormReturn } from 'react-hook-form';
import { clamp } from 'lodash';
import { useFormFieldValue } from './useFormFieldValue';

// Hook for boundary validation and clamping
export const useBoundaryValidation = <T extends FieldValues>(
  form: UseFormReturn<T>,
  name: Path<T>,
  minValue?: number,
  maxValue?: number,
) => {
  const { currentValue, updateFormValue, isUpdatingRef } = useFormFieldValue(
    form,
    name,
  );
  const prevMinMaxRef = useRef({ minValue, maxValue });

  useEffect(() => {
    const prevMinMax = prevMinMaxRef.current;
    const hasMinMaxChanged =
      prevMinMax.minValue !== minValue || prevMinMax.maxValue !== maxValue;

    if (hasMinMaxChanged && minValue !== undefined && maxValue !== undefined) {
      prevMinMaxRef.current = { minValue, maxValue };

      if (
        currentValue !== undefined &&
        currentValue !== null &&
        !isUpdatingRef.current &&
        typeof currentValue === 'number'
      ) {
        const clamped = clamp(currentValue, minValue, maxValue);
        if (clamped !== currentValue) updateFormValue(clamped);
      }
    }
  }, [minValue, maxValue, currentValue, updateFormValue, isUpdatingRef]);

  return { currentValue, updateFormValue };
};
