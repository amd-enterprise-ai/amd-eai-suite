// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, fireEvent, render, screen } from '@testing-library/react';
import { createRef } from 'react';

import { FormField } from '@/types/forms/forms';

import FormFieldComponent from '@/components/shared/ManagedForm/FormFieldComponent';
import ManagedForm from '@/components/shared/ManagedForm/ManagedForm';

import { ZodType, z } from 'zod';

type TestFormFields = 'name' | 'email';

type SampleFormData = {
  [key in TestFormFields]: string;
};

const sampleFormSchema: ZodType<SampleFormData> = z.object({
  name: z.string().trim().nonempty('Username is required'),
  email: z
    .string()
    .trim()
    .nonempty('Email is required')
    .email('Valid email is required'),
});

const formElements: FormField<SampleFormData>[] = [
  {
    name: 'name',
    label: 'Name',
    isRequired: true,
  },
  {
    name: 'email',
    label: 'Email',
    isRequired: true,
  },
];

describe('ManagedForm', () => {
  it('renders form elements', () => {
    const mockOnFormSuccess = vi.fn();
    act(() => {
      render(
        <ManagedForm<SampleFormData>
          onFormSuccess={mockOnFormSuccess}
          validationSchema={sampleFormSchema}
          defaultValues={{
            name: '',
            email: '',
          }}
          renderFields={(form) => (
            <>
              {formElements.map((field) => (
                <FormFieldComponent<SampleFormData>
                  key={field.name}
                  formField={{
                    name: field.name,
                    label: field.label,
                  }}
                  defaultValue={
                    form.formState.defaultValues?.[field.name] ?? ''
                  }
                  register={form.register}
                />
              ))}
            </>
          )}
        />,
      );
    });

    expect(screen.getByLabelText('Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
  });

  it('displays validation errors on submit', async () => {
    const mockOnFormSuccess = vi.fn();
    await act(() => {
      render(
        <ManagedForm<SampleFormData>
          showSubmitButton={true}
          submitButtonText={'submit button'}
          onFormSuccess={mockOnFormSuccess}
          validationSchema={sampleFormSchema}
          renderFields={(form) => (
            <>
              {formElements.map((field) => (
                <FormFieldComponent<SampleFormData>
                  key={field.name}
                  formField={{
                    name: field.name,
                    label: field.label,
                  }}
                  defaultValue={
                    form.formState.defaultValues?.[field.name] ?? ''
                  }
                  register={form.register}
                />
              ))}
            </>
          )}
        />,
      );
    });

    await act(() => {
      fireEvent.submit(screen.getByText('submit button'));
    });

    expect(screen.getByLabelText('Name')).toHaveFocus();
  });

  it('calls onFormSuccess with form data when validation passes', async () => {
    const mockOnFormSuccess = vi.fn();
    await act(() => {
      render(
        <ManagedForm<SampleFormData>
          showSubmitButton={true}
          submitButtonText={'submit button'}
          onFormSuccess={mockOnFormSuccess}
          validationSchema={sampleFormSchema}
          renderFields={(form) => (
            <>
              {formElements.map((field) => (
                <FormFieldComponent<SampleFormData>
                  key={field.name}
                  formField={{
                    name: field.name,
                    label: field.label,
                  }}
                  defaultValue={
                    form.formState.defaultValues?.[field.name] ?? ''
                  }
                  register={form.register}
                />
              ))}
            </>
          )}
        />,
      );
    });

    await act(() => {
      fireEvent.change(screen.getByLabelText('Name'), {
        target: { value: 'John Doe' },
      });
      fireEvent.change(screen.getByLabelText('Email'), {
        target: { value: 'john@example.com' },
      });

      fireEvent.submit(screen.getByText('submit button'));
    });

    expect(mockOnFormSuccess).toHaveBeenCalledWith({
      name: 'John Doe',
      email: 'john@example.com',
    });
  });

  it('calls onFormFailure with errors when validation fails', async () => {
    const mockOnFormFailure = vi.fn();
    const mockOnFormSuccess = vi.fn();
    await act(() => {
      render(
        <ManagedForm<SampleFormData>
          showSubmitButton={true}
          submitButtonText={'submit button'}
          onFormSuccess={mockOnFormSuccess}
          onFormFailure={mockOnFormFailure}
          validationSchema={sampleFormSchema}
          renderFields={(form) => (
            <>
              {formElements.map((field) => (
                <FormFieldComponent<SampleFormData>
                  key={field.name}
                  formField={{
                    name: field.name,
                    label: field.label,
                  }}
                  defaultValue={
                    form.formState.defaultValues?.[field.name] ?? ''
                  }
                  register={form.register}
                />
              ))}
            </>
          )}
        />,
      );
    });

    await act(() => {
      fireEvent.submit(screen.getByText('submit button'));
    });

    expect(mockOnFormFailure).toHaveBeenCalledWith(
      {
        email: {
          message: 'Email is required',
          type: 'too_small',
          ref: expect.anything(),
        },
        name: {
          message: 'Username is required',
          type: 'too_small',
          ref: expect.anything(),
        },
      },
      { email: expect.anything(), name: expect.anything() },
    );
  });

  it('triggers submit event using ref', async () => {
    const formRef = createRef<HTMLFormElement>();
    const mockOnFormFailure = vi.fn();
    const mockOnFormSuccess = vi.fn();
    await act(() => {
      render(
        <ManagedForm<SampleFormData>
          formRef={formRef}
          showSubmitButton={true}
          submitButtonText={'submit button'}
          onFormSuccess={mockOnFormSuccess}
          onFormFailure={mockOnFormFailure}
          validationSchema={sampleFormSchema}
          renderFields={(form) => (
            <>
              {formElements.map((field) => (
                <FormFieldComponent<SampleFormData>
                  key={field.name}
                  formField={{
                    name: field.name,
                    label: field.label,
                  }}
                  defaultValue={
                    form.formState.defaultValues?.[field.name] ?? ''
                  }
                  register={form.register}
                />
              ))}
            </>
          )}
        />,
      );
    });

    await act(() => {
      fireEvent.change(screen.getByLabelText('Name'), {
        target: { value: 'John Doe' },
      });
      fireEvent.change(screen.getByLabelText('Email'), {
        target: { value: 'john@example.com' },
      });
      if (formRef.current) {
        fireEvent.submit(formRef.current);
      }
    });

    expect(screen.queryByText('Name is required')).not.toBeInTheDocument();
    expect(
      screen.queryByText('Valid email is required'),
    ).not.toBeInTheDocument();
  });

  it('resets the form back to initial values', async () => {
    const initialValues = {
      name: 'Initial Name',
      email: 'initial@example.com',
    };

    const mockOnFormFailure = vi.fn();
    const mockOnFormSuccess = vi.fn();
    await act(() => {
      render(
        <ManagedForm<SampleFormData>
          defaultValues={initialValues}
          showSubmitButton
          submitButtonText={'submit button'}
          showResetButton
          resetButtonText="Discard Changes"
          onFormSuccess={mockOnFormSuccess}
          onFormFailure={mockOnFormFailure}
          validationSchema={sampleFormSchema}
          renderFields={(form) => (
            <>
              {formElements.map((field) => (
                <FormFieldComponent<SampleFormData>
                  key={field.name}
                  formField={{
                    name: field.name,
                    label: field.label,
                  }}
                  defaultValue={
                    form.formState.defaultValues?.[field.name] ?? ''
                  }
                  register={form.register}
                />
              ))}
            </>
          )}
        />,
      );
    });

    await act(() => {
      fireEvent.change(screen.getByLabelText('Name'), {
        target: { value: 'Changed Name' },
      });
      fireEvent.change(screen.getByLabelText('Email'), {
        target: { value: 'changed@example.com' },
      });
    });

    expect(screen.getByLabelText('Name')).toHaveValue('Changed Name');
    expect(screen.getByLabelText('Email')).toHaveValue('changed@example.com');

    await act(() => {
      fireEvent.click(screen.getByText('Discard Changes'));
    });

    expect(screen.getByLabelText('Name')).toHaveValue('Initial Name');
    expect(screen.getByLabelText('Email')).toHaveValue('initial@example.com');
  });

  it('resets the form using ref.current method', async () => {
    const initialValues = {
      name: 'Initial Name',
      email: 'initial@example.com',
    };

    const formRef = createRef<HTMLFormElement>();

    const mockOnFormFailure = vi.fn();
    const mockOnFormSuccess = vi.fn();
    await act(() => {
      render(
        <ManagedForm<SampleFormData>
          formRef={formRef}
          defaultValues={initialValues}
          showSubmitButton
          submitButtonText={'submit button'}
          showResetButton
          resetButtonText="Discard Changes"
          onFormSuccess={mockOnFormSuccess}
          onFormFailure={mockOnFormFailure}
          validationSchema={sampleFormSchema}
          renderFields={(form) => (
            <>
              {formElements.map((field) => (
                <FormFieldComponent<SampleFormData>
                  key={field.name}
                  formField={{
                    name: field.name,
                    label: field.label,
                  }}
                  defaultValue={
                    form.formState.defaultValues?.[field.name] ?? ''
                  }
                  register={form.register}
                />
              ))}
            </>
          )}
        />,
      );
    });

    await act(() => {
      fireEvent.change(screen.getByLabelText('Name'), {
        target: { value: 'Changed Name' },
      });
      fireEvent.change(screen.getByLabelText('Email'), {
        target: { value: 'changed@example.com' },
      });
    });

    expect(screen.getByLabelText('Name')).toHaveValue('Changed Name');
    expect(screen.getByLabelText('Email')).toHaveValue('changed@example.com');

    await act(() => {
      if (formRef.current) {
        formRef.current.reset();
      }
    });

    expect(screen.getByLabelText('Name')).toHaveValue('Initial Name');
    expect(screen.getByLabelText('Email')).toHaveValue('initial@example.com');
  });
});
