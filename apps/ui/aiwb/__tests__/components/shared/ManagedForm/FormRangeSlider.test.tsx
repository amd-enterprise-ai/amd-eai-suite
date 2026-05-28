// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, render, screen } from '@testing-library/react';
import { UseFormReturn } from 'react-hook-form';
import { z, ZodType } from 'zod';

import { FormRangeSlider, ManagedForm } from '@amdenterpriseai/components';

type FormData = { min: number; max: number };

const schema: ZodType<FormData> = z.object({
  min: z.number(),
  max: z.number(),
});

const renderFormRangeSlider = (
  formProps: Partial<React.ComponentProps<typeof ManagedForm<FormData>>> = {},
) => {
  let formRef: UseFormReturn<FormData> | undefined;

  const result = render(
    <ManagedForm<FormData>
      onFormSuccess={vi.fn()}
      validationSchema={schema}
      defaultValues={{ min: 1, max: 10 }}
      {...formProps}
      renderFields={(form) => {
        formRef = form;
        return (
          <FormRangeSlider<FormData>
            form={form}
            minName="min"
            maxName="max"
            minValue={0}
            maxValue={20}
            aria-label="Replica range"
          />
        );
      }}
    />,
  );

  return { ...result, getForm: () => formRef };
};

describe('FormRangeSlider', () => {
  it('renders two slider thumbs for the range', () => {
    renderFormRangeSlider();

    const sliders = screen.getAllByRole('slider');
    expect(sliders).toHaveLength(2);
  });

  it('reflects default values in form state', async () => {
    const { getForm } = renderFormRangeSlider();

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    const form = getForm()!;
    expect(form.getValues('min')).toBe(1);
    expect(form.getValues('max')).toBe(10);
  });

  it('unregisters both fields when unmounted', async () => {
    let formRef: UseFormReturn<FormData> | undefined;

    const { rerender } = render(
      <ManagedForm<FormData>
        onFormSuccess={vi.fn()}
        validationSchema={schema}
        defaultValues={{ min: 2, max: 8 }}
        renderFields={(form) => {
          formRef = form;
          return (
            <FormRangeSlider<FormData>
              form={form}
              minName="min"
              maxName="max"
              minValue={0}
              maxValue={20}
              aria-label="Replica range"
            />
          );
        }}
      />,
    );

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(formRef!.getValues('min')).toBe(2);
    expect(formRef!.getValues('max')).toBe(8);

    // Remove the slider from the form
    await act(async () => {
      rerender(
        <ManagedForm<FormData>
          onFormSuccess={vi.fn()}
          validationSchema={schema}
          defaultValues={{ min: 2, max: 8 }}
          renderFields={(form) => {
            formRef = form;
            return <div />;
          }}
        />,
      );
    });

    // Fields should be unregistered — getValues returns undefined
    expect(formRef!.getValues('min')).toBeUndefined();
    expect(formRef!.getValues('max')).toBeUndefined();
  });
});
