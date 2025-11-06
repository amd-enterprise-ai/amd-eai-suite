// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, renderHook } from '@testing-library/react';
import { useForm } from 'react-hook-form';

import { useFormFieldValue } from '../../hooks/useFormFieldValue';

// Define test form data type
interface TestFormData {
  stringField: string;
  numberField: number;
  optionalField?: string;
}

describe('useFormFieldValue', () => {
  const defaultValues: TestFormData = {
    stringField: 'initial',
    numberField: 10,
    optionalField: 'optional',
  };

  it('should return the initial field value', () => {
    const { result } = renderHook(() => {
      const form = useForm<TestFormData>({ defaultValues });
      return { form, hook: useFormFieldValue(form, 'stringField') };
    });

    expect(result.current.hook.currentValue).toBe('initial');
  });

  it('should return the initial number field value', () => {
    const { result } = renderHook(() => {
      const form = useForm<TestFormData>({ defaultValues });
      return { form, hook: useFormFieldValue(form, 'numberField') };
    });

    expect(result.current.hook.currentValue).toBe(10);
  });

  it('should update currentValue when form field changes externally', () => {
    const { result } = renderHook(() => {
      const form = useForm<TestFormData>({ defaultValues });
      return { form, hook: useFormFieldValue(form, 'stringField') };
    });

    expect(result.current.hook.currentValue).toBe('initial');

    // Change the form value externally
    act(() => {
      result.current.form.setValue('stringField', 'updated');
    });

    expect(result.current.hook.currentValue).toBe('updated');
  });

  it('should update currentValue when number field changes externally', () => {
    const { result } = renderHook(() => {
      const form = useForm<TestFormData>({ defaultValues });
      return { form, hook: useFormFieldValue(form, 'numberField') };
    });

    expect(result.current.hook.currentValue).toBe(10);

    // Change the form value externally
    act(() => {
      result.current.form.setValue('numberField', 25);
    });

    expect(result.current.hook.currentValue).toBe(25);
  });

  it('should update form value using updateFormValue function with number', () => {
    const { result } = renderHook(() => {
      const form = useForm<TestFormData>({ defaultValues });
      return { form, hook: useFormFieldValue(form, 'numberField') };
    });

    expect(result.current.hook.currentValue).toBe(10);

    // Update using the hook's updateFormValue function
    act(() => {
      result.current.hook.updateFormValue(42);
    });

    expect(result.current.form.getValues('numberField')).toBe(42);
  });

  it('should call setValue with shouldValidate: true when updating form value', () => {
    const { result } = renderHook(() => {
      const form = useForm<TestFormData>({ defaultValues });
      return { form, hook: useFormFieldValue(form, 'numberField') };
    });

    // Spy on the form's setValue method
    const setValueSpy = vi.spyOn(result.current.form, 'setValue');

    act(() => {
      result.current.hook.updateFormValue(100);
    });

    expect(setValueSpy).toHaveBeenCalledWith('numberField', 100, {
      shouldValidate: true,
    });
  });

  it('should not update currentValue when updating through updateFormValue to prevent infinite loops', async () => {
    const { result } = renderHook(() => {
      const form = useForm<TestFormData>({ defaultValues });
      return { form, hook: useFormFieldValue(form, 'numberField') };
    });

    const initialValue = result.current.hook.currentValue;

    // Mock the watch subscription to track how many times it's called
    const watchSpy = vi.spyOn(result.current.form, 'watch');

    act(() => {
      result.current.hook.updateFormValue(50);
    });

    // Wait for the promise to resolve and flag to reset
    await act(async () => {
      await Promise.resolve();
    });

    // Verify that the isUpdatingRef flag is managed correctly
    expect(result.current.hook.isUpdatingRef.current).toBe(false);
    expect(result.current.form.getValues('numberField')).toBe(50);
  });

  it('should handle updates to different fields without affecting watched field', () => {
    const { result } = renderHook(() => {
      const form = useForm<TestFormData>({ defaultValues });
      return { form, hook: useFormFieldValue(form, 'stringField') };
    });

    expect(result.current.hook.currentValue).toBe('initial');

    // Update a different field
    act(() => {
      result.current.form.setValue('numberField', 999);
    });

    // The watched field should remain unchanged
    expect(result.current.hook.currentValue).toBe('initial');
  });

  it('should handle optional fields correctly', () => {
    const { result } = renderHook(() => {
      const form = useForm<TestFormData>({ defaultValues });
      return { form, hook: useFormFieldValue(form, 'optionalField') };
    });

    expect(result.current.hook.currentValue).toBe('optional');

    // Update the optional field
    act(() => {
      result.current.form.setValue('optionalField', 'new optional value');
    });

    expect(result.current.hook.currentValue).toBe('new optional value');
  });

  it('should handle undefined values correctly', () => {
    const { result } = renderHook(() => {
      const form = useForm<TestFormData>({
        defaultValues: { ...defaultValues, optionalField: undefined },
      });
      return { form, hook: useFormFieldValue(form, 'optionalField') };
    });

    expect(result.current.hook.currentValue).toBeUndefined();

    // Update the undefined field
    act(() => {
      result.current.form.setValue('optionalField', 'now defined');
    });

    expect(result.current.hook.currentValue).toBe('now defined');
  });

  it('should clean up subscription when unmounted', () => {
    // Mock the unsubscribe function before rendering
    const unsubscribeSpy = vi.fn();
    const mockSubscription = { unsubscribe: unsubscribeSpy };

    const { result, unmount } = renderHook(() => {
      const form = useForm<TestFormData>({ defaultValues });

      // Mock the watch method to return our mock subscription
      vi.spyOn(form, 'watch').mockReturnValue(mockSubscription);

      return { form, hook: useFormFieldValue(form, 'stringField') };
    });

    // Unmount the hook
    unmount();

    // Verify that unsubscribe was called
    expect(unsubscribeSpy).toHaveBeenCalled();
  });

  it('should maintain stable updateFormValue function reference', () => {
    const { result, rerender } = renderHook(() => {
      const form = useForm<TestFormData>({ defaultValues });
      return { form, hook: useFormFieldValue(form, 'numberField') };
    });

    const firstUpdateFormValue = result.current.hook.updateFormValue;

    // Re-render the hook
    rerender();

    // The function reference should remain stable
    expect(result.current.hook.updateFormValue).toBe(firstUpdateFormValue);
  });

  it('should handle rapid consecutive updates correctly', async () => {
    const { result } = renderHook(() => {
      const form = useForm<TestFormData>({ defaultValues });
      return { form, hook: useFormFieldValue(form, 'numberField') };
    });

    // Perform rapid consecutive updates
    act(() => {
      result.current.hook.updateFormValue(100);
      result.current.hook.updateFormValue(200);
      result.current.hook.updateFormValue(300);
    });

    // Wait for all promises to resolve
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
    });

    // Final value should be the last one set
    expect(result.current.form.getValues('numberField')).toBe(300);
    expect(result.current.hook.isUpdatingRef.current).toBe(false);
  });
});
