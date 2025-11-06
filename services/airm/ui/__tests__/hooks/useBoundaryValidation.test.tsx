// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, renderHook } from '@testing-library/react';
import { useForm } from 'react-hook-form';

import { useBoundaryValidation } from '../../hooks/useBoundaryValidation';

// Define test form data type
interface TestFormData {
  numberField: number;
  optionalField?: number;
}

describe('useBoundaryValidation', () => {
  const defaultValues: TestFormData = {
    numberField: 10,
    optionalField: 20,
  };

  const setupHook = (
    fieldName: keyof TestFormData,
    minValue?: number,
    maxValue?: number,
    initialValues: Partial<TestFormData> = defaultValues,
  ) => {
    return renderHook(
      ({ min, max }) => {
        const form = useForm<TestFormData>({
          defaultValues: { ...defaultValues, ...initialValues },
        });
        const boundaryValidation = useBoundaryValidation(
          form,
          fieldName as any,
          min,
          max,
        );
        return { form, boundaryValidation };
      },
      {
        initialProps: { min: minValue, max: maxValue },
      },
    );
  };

  describe('number field validation', () => {
    it('should return current value and update function', () => {
      const { result } = setupHook('numberField', 0, 100);

      expect(result.current.boundaryValidation.currentValue).toBe(10);
      expect(typeof result.current.boundaryValidation.updateFormValue).toBe(
        'function',
      );
    });

    it('should not clamp initial values on first render', () => {
      const { result } = setupHook('numberField', 0, 100, { numberField: 150 });

      // The hook does not clamp initial values automatically
      expect(result.current.form.getValues('numberField')).toBe(150);
    });

    it('should not clamp initial values below minimum', () => {
      const { result } = setupHook('numberField', 0, 100, { numberField: -10 });

      // The hook does not clamp initial values automatically
      expect(result.current.form.getValues('numberField')).toBe(-10);
    });

    it('should not modify value when it is within boundaries', () => {
      const { result } = setupHook('numberField', 0, 100, { numberField: 50 });

      // The value should remain unchanged
      expect(result.current.form.getValues('numberField')).toBe(50);
    });

    it('should handle undefined min/max values', () => {
      const { result } = setupHook('numberField', undefined, undefined, {
        numberField: 150,
      });

      // No clamping should occur
      expect(result.current.form.getValues('numberField')).toBe(150);
    });

    it('should handle only minimum boundary', () => {
      const { result } = setupHook('numberField', 20, undefined, {
        numberField: 10,
      });

      // No clamping should occur since maxValue is undefined
      expect(result.current.form.getValues('numberField')).toBe(10);
    });

    it('should handle only maximum boundary', () => {
      const { result } = setupHook('numberField', undefined, 50, {
        numberField: 100,
      });

      // No clamping should occur since minValue is undefined
      expect(result.current.form.getValues('numberField')).toBe(100);
    });
  });

  describe('boundary changes', () => {
    it('should re-clamp value when min/max boundaries change', async () => {
      const { result, rerender } = setupHook('numberField', 0, 100, {
        numberField: 50,
      });

      // Initial value should be within bounds
      expect(result.current.form.getValues('numberField')).toBe(50);

      // Change boundaries to make current value out of bounds
      await act(async () => {
        rerender({ min: 60, max: 80 });
        // Wait for the Promise.resolve() in useFormFieldValue
        await new Promise((resolve) => setTimeout(resolve, 0));
      });

      // Value should be clamped to new minimum
      expect(result.current.form.getValues('numberField')).toBe(60);
    });

    it('should not re-clamp when boundaries change but value is already within new bounds', async () => {
      const { result, rerender } = setupHook('numberField', 0, 100, {
        numberField: 50,
      });

      expect(result.current.form.getValues('numberField')).toBe(50);

      // Change boundaries but keep current value within bounds
      await act(async () => {
        rerender({ min: 40, max: 60 });
        // Wait for the Promise.resolve() in useFormFieldValue
        await new Promise((resolve) => setTimeout(resolve, 0));
      });

      // Value should remain unchanged
      expect(result.current.form.getValues('numberField')).toBe(50);
    });

    it('should clamp when min/max are initially undefined then defined', async () => {
      const { result, rerender } = setupHook(
        'numberField',
        undefined,
        undefined,
        {
          numberField: 150,
        },
      );

      // Initial value should not be clamped
      expect(result.current.form.getValues('numberField')).toBe(150);

      // Set boundaries for the first time
      await act(async () => {
        rerender({ min: 0, max: 100 });
        // Wait for the Promise.resolve() in useFormFieldValue
        await new Promise((resolve) => setTimeout(resolve, 0));
      });

      // Value should now be clamped
      expect(result.current.form.getValues('numberField')).toBe(100);
    });

    it('should not clamp when only one boundary is defined', async () => {
      const { result, rerender } = setupHook(
        'numberField',
        undefined,
        undefined,
        {
          numberField: 150,
        },
      );

      // Set only minimum boundary
      await act(async () => {
        rerender({ min: 0, max: undefined });
        // Wait for the Promise.resolve() in useFormFieldValue
        await new Promise((resolve) => setTimeout(resolve, 0));
      });

      // Value should not be clamped since max is undefined
      expect(result.current.form.getValues('numberField')).toBe(150);
    });
  });

  describe('edge cases', () => {
    it('should handle null values', () => {
      const { result } = setupHook('optionalField', 0, 100, {
        optionalField: undefined,
      });

      // Should not throw an error with undefined value
      expect(
        () => result.current.boundaryValidation.currentValue,
      ).not.toThrow();
    });

    it('should not clamp initial value when min equals max', () => {
      const { result } = setupHook('numberField', 50, 50, { numberField: 100 });

      // Value should not be clamped on initial render
      expect(result.current.form.getValues('numberField')).toBe(100);
    });

    it('should not clamp initial value with negative boundaries', () => {
      const { result } = setupHook('numberField', -100, -10, {
        numberField: 50,
      });

      // Value should not be clamped on initial render
      expect(result.current.form.getValues('numberField')).toBe(50);
    });

    it('should not clamp initial value with decimal boundaries', () => {
      const { result } = setupHook('numberField', 1.5, 2.5, { numberField: 3 });

      // Value should not be clamped on initial render
      expect(result.current.form.getValues('numberField')).toBe(3);
    });

    it('should handle zero as a valid boundary value', async () => {
      // Test clamp to zero - this tests the fix for the truthy check bug
      const { result, rerender } = setupHook(
        'numberField',
        undefined,
        undefined,
        {
          numberField: -5,
        },
      );

      // Initial value should not be clamped
      expect(result.current.form.getValues('numberField')).toBe(-5);

      // Set boundaries for the first time
      await act(async () => {
        rerender({ min: 0, max: 10 });
        // Wait for the Promise.resolve() in useFormFieldValue
        await new Promise((resolve) => setTimeout(resolve, 0));
      });

      // Value should now be clamped to 0 (minimum boundary)
      expect(result.current.form.getValues('numberField')).toBe(0);
    });

    it('should handle very large numbers', async () => {
      const { result, rerender } = setupHook(
        'numberField',
        undefined,
        undefined,
        {
          numberField: Number.MAX_SAFE_INTEGER + 1,
        },
      );

      await act(async () => {
        rerender({ min: 0, max: Number.MAX_SAFE_INTEGER });
        await new Promise((resolve) => setTimeout(resolve, 0));
      });

      expect(result.current.form.getValues('numberField')).toBe(
        Number.MAX_SAFE_INTEGER,
      );
    });
  });

  describe('integration with form updates', () => {
    it('should update form value using updateFormValue function', async () => {
      const { result } = setupHook('numberField', 0, 100);

      await act(async () => {
        result.current.boundaryValidation.updateFormValue(75);
        // Wait for the Promise.resolve() in useFormFieldValue
        await new Promise((resolve) => setTimeout(resolve, 0));
      });

      expect(result.current.form.getValues('numberField')).toBe(75);
    });

    it('should not interfere with manual form updates', async () => {
      const { result } = setupHook('numberField', 0, 100);

      // Manually update the form value
      await act(async () => {
        result.current.form.setValue('numberField', 85);
        // Wait for the Promise.resolve() in useFormFieldValue
        await new Promise((resolve) => setTimeout(resolve, 0));
      });

      expect(result.current.form.getValues('numberField')).toBe(85);
    });
  });
});
