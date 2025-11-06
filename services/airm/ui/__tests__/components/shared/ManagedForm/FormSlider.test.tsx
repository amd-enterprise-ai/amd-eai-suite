// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, fireEvent, render, screen } from '@testing-library/react';

import FormSlider from '@/components/shared/ManagedForm/FormSlider';
import ManagedForm from '@/components/shared/ManagedForm/ManagedForm';

import { ZodType, z } from 'zod';

type SampleFormData = {
  value: number;
};

const sampleFormSchema: ZodType<SampleFormData> = z.object({
  value: z
    .number()
    .min(0, 'Value must be at least 0')
    .max(100, 'Value must be at most 100'),
});

// Helper function to render FormSlider with common props
const renderFormSlider = (
  formProps: Partial<
    React.ComponentProps<typeof ManagedForm<SampleFormData>>
  > = {},
  sliderProps: Partial<
    React.ComponentProps<typeof FormSlider<SampleFormData>>
  > = {},
) => {
  const defaultFormProps = {
    onFormSuccess: vi.fn(),
    validationSchema: sampleFormSchema,
    defaultValues: { value: 50 },
  };

  return render(
    <ManagedForm<SampleFormData>
      {...defaultFormProps}
      {...formProps}
      renderFields={(form) => (
        <FormSlider<SampleFormData>
          form={form}
          name="value"
          label="Value"
          minValue={0}
          maxValue={100}
          {...sliderProps}
        />
      )}
    />,
  );
};

describe('FormSlider', () => {
  it('renders slider with label', () => {
    renderFormSlider();

    expect(screen.getByRole('slider')).toBeInTheDocument();
    expect(screen.getByRole('slider')).toHaveAttribute('aria-labelledby');
  });

  it('renders with description text', () => {
    const description = 'Select a value between 0 and 100';
    renderFormSlider({}, { description });

    expect(screen.getByText(description)).toBeInTheDocument();
  });

  it('displays validation error when value is out of range', async () => {
    const outOfRangeSchema = z.object({
      value: z.number().min(10, 'Value must be at least 10'),
    });

    render(
      <ManagedForm<{ value: number }>
        defaultValues={{ value: 5 }}
        showSubmitButton={true}
        submitButtonText="Submit"
        onFormSuccess={vi.fn()}
        validationSchema={outOfRangeSchema}
        renderFields={(form) => (
          <FormSlider<{ value: number }>
            form={form}
            name="value"
            label="Value"
            minValue={0}
            maxValue={100}
          />
        )}
      />,
    );

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
    });

    expect(screen.getByText('Value must be at least 10')).toBeInTheDocument();
  });

  it('handles value changes and form submission', async () => {
    const mockOnFormSuccess = vi.fn();

    const simpleSchema = z.object({
      value: z.number(),
    });

    render(
      <ManagedForm<{ value: number }>
        defaultValues={{ value: 50 }}
        showSubmitButton={true}
        submitButtonText="Submit"
        onFormSuccess={mockOnFormSuccess}
        validationSchema={simpleSchema}
        renderFields={(form) => (
          <FormSlider<{ value: number }>
            form={form}
            name="value"
            label="Value"
            minValue={0}
            maxValue={100}
          />
        )}
      />,
    );

    const slider = screen.getByRole('slider');

    // Change slider value
    await act(async () => {
      fireEvent.change(slider, { target: { value: '75' } });
    });

    // Submit form
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
    });

    // Wait for form processing
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 200));
    });

    expect(mockOnFormSuccess).toHaveBeenCalledWith(
      expect.objectContaining({ value: 75 }),
    );
  });

  it('displays error styling when field is invalid', async () => {
    const errorSchema = z.object({
      value: z.number().min(50, 'Value must be at least 50'),
    });

    render(
      <ManagedForm<{ value: number }>
        defaultValues={{ value: 25 }}
        showSubmitButton={true}
        submitButtonText="Submit"
        onFormSuccess={vi.fn()}
        validationSchema={errorSchema}
        renderFields={(form) => (
          <FormSlider<{ value: number }>
            form={form}
            name="value"
            label="Value"
            minValue={0}
            maxValue={100}
          />
        )}
      />,
    );

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
    });

    expect(screen.getByText('Value must be at least 50')).toBeInTheDocument();

    // Check for error styling via data attributes or classes instead of aria-invalid
    const errorText = screen.getByText('Value must be at least 50');
    expect(errorText).toHaveClass('text-danger');
  });

  it('handles disabled state', () => {
    renderFormSlider({}, { isDisabled: true });

    const slider = screen.getByRole('slider');
    expect(slider).toBeDisabled();
  });

  it('applies custom className correctly', () => {
    const customClass = 'custom-slider-class';
    renderFormSlider({}, { className: customClass });

    const componentContainer = document.querySelector(`.${customClass}`);
    expect(componentContainer).toBeInTheDocument();
  });

  it('clears error message when input becomes valid', async () => {
    const validationSchema = z.object({
      value: z.number().min(50, 'Value must be at least 50'),
    });

    render(
      <ManagedForm<{ value: number }>
        defaultValues={{ value: 25 }}
        showSubmitButton={true}
        submitButtonText="Submit"
        onFormSuccess={vi.fn()}
        validationSchema={validationSchema}
        renderFields={(form) => (
          <FormSlider<{ value: number }>
            form={form}
            name="value"
            label="Value"
            minValue={0}
            maxValue={100}
          />
        )}
      />,
    );

    // First, trigger validation error
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
    });

    expect(screen.getByText('Value must be at least 50')).toBeInTheDocument();

    // Then, provide valid input
    const slider = screen.getByRole('slider');
    await act(async () => {
      fireEvent.change(slider, { target: { value: '75' } });
    });

    // Error message should be cleared
    expect(
      screen.queryByText('Value must be at least 50'),
    ).not.toBeInTheDocument();
  });

  it('resets form values to initial state', async () => {
    const initialValues = { value: 30 };

    renderFormSlider({
      defaultValues: initialValues,
      showSubmitButton: true,
      submitButtonText: 'Submit',
      showResetButton: true,
      resetButtonText: 'Reset',
    });

    const slider = screen.getByRole('slider');

    // Change slider value
    await act(async () => {
      fireEvent.change(slider, { target: { value: '70' } });
    });

    expect(slider).toHaveValue('70');

    // Reset form using the button
    await act(async () => {
      fireEvent.click(screen.getByText('Reset'));
    });

    // Verify reset to initial value
    expect(slider).toHaveValue('30');
  });

  it('maintains number type consistency with multiple sliders', async () => {
    const twoSliderSchema = z.object({
      value1: z.number(),
      value2: z.number(),
    });

    let formRef: any;

    render(
      <ManagedForm<{ value1: number; value2: number }>
        defaultValues={{ value1: 10, value2: 20 }}
        showSubmitButton={true}
        submitButtonText="Submit"
        onFormSuccess={vi.fn()}
        validationSchema={twoSliderSchema}
        renderFields={(form) => {
          formRef = form;
          return (
            <div>
              <div data-testid="slider1">
                <FormSlider<{ value1: number; value2: number }>
                  form={form}
                  name="value1"
                  label="Value 1"
                  minValue={0}
                  maxValue={100}
                />
              </div>
              <div data-testid="slider2">
                <FormSlider<{ value1: number; value2: number }>
                  form={form}
                  name="value2"
                  label="Value 2"
                  minValue={0}
                  maxValue={100}
                />
              </div>
            </div>
          );
        }}
      />,
    );

    const sliders = screen.getAllByRole('slider');
    expect(sliders).toHaveLength(2);

    const slider1 = sliders[0];
    const slider2 = sliders[1];

    // Change first slider value
    await act(async () => {
      fireEvent.change(slider1, { target: { value: '30' } });
      // Wait for async conversion
      await new Promise((resolve) => setTimeout(resolve, 20));
    });

    // Verify first slider value is number
    expect(formRef.getValues('value1')).toBe(30);
    expect(typeof formRef.getValues('value1')).toBe('number');

    // Change second slider value
    await act(async () => {
      fireEvent.change(slider2, { target: { value: '40' } });
      // Wait for async conversion
      await new Promise((resolve) => setTimeout(resolve, 20));
    });

    // Verify both values are still numbers (the bug would convert the first value to string)
    expect(formRef.getValues('value1')).toBe(30);
    expect(typeof formRef.getValues('value1')).toBe('number');
    expect(formRef.getValues('value2')).toBe(40);
    expect(typeof formRef.getValues('value2')).toBe('number');

    // Change first slider again
    await act(async () => {
      fireEvent.change(slider1, { target: { value: '50' } });
      // Wait for async conversion
      await new Promise((resolve) => setTimeout(resolve, 20));
    });

    // Verify all values remain numbers
    expect(formRef.getValues('value1')).toBe(50);
    expect(typeof formRef.getValues('value1')).toBe('number');
    expect(formRef.getValues('value2')).toBe(40);
    expect(typeof formRef.getValues('value2')).toBe('number');
  });
});
