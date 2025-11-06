// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { SelectItem } from '@heroui/react';
import { IconUser } from '@tabler/icons-react';
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';

import FormSelect from '@/components/shared/ManagedForm/FormSelect';
import ManagedForm from '@/components/shared/ManagedForm/ManagedForm';

import { ZodType, z } from 'zod';

type SampleFormData = {
  category: string;
};

const sampleFormSchema: ZodType<SampleFormData> = z.object({
  category: z.string().nonempty('Category is required'),
});

const categoryOptions = [
  { key: 'development', label: 'Development' },
  { key: 'design', label: 'Design' },
  { key: 'testing', label: 'Testing' },
];

// Helper function to render FormSelect with common props
const renderFormSelect = (
  formProps: Partial<
    React.ComponentProps<typeof ManagedForm<SampleFormData>>
  > = {},
  selectProps: Partial<
    React.ComponentProps<typeof FormSelect<SampleFormData>>
  > = {},
) => {
  const defaultFormProps = {
    onFormSuccess: vi.fn(),
    validationSchema: sampleFormSchema,
    defaultValues: { category: '', priority: '' },
  };

  return render(
    <ManagedForm<SampleFormData>
      {...defaultFormProps}
      {...formProps}
      renderFields={(form) => (
        <FormSelect<SampleFormData>
          form={form}
          name="category"
          label="Category"
          placeholder="Select a category"
          {...selectProps}
        >
          {categoryOptions.map((option) => (
            <SelectItem key={option.key}>{option.label}</SelectItem>
          ))}
        </FormSelect>
      )}
    />,
  );
};

describe('FormSelect', () => {
  it('renders select with label and placeholder', () => {
    renderFormSelect();

    expect(
      screen.getByRole('button', { name: /Category/ }),
    ).toBeInTheDocument();
  });

  it('renders select with icon', () => {
    renderFormSelect({}, { icon: IconUser });

    expect(
      screen.getByRole('button', { name: /Category/ }),
    ).toBeInTheDocument();
  });

  it('displays validation error when required field is empty', async () => {
    renderFormSelect({
      showSubmitButton: true,
      submitButtonText: 'Submit',
    });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
    });

    expect(screen.getByText('Category is required')).toBeInTheDocument();
  });

  it('handles selection and form submission', async () => {
    const mockOnFormSuccess = vi.fn();

    // Use a simple schema with just one required field for testing
    const simpleSchema = z.object({
      category: z.string().nonempty('Category is required'),
    });

    render(
      <ManagedForm<{ category: string }>
        defaultValues={{ category: '' }}
        showSubmitButton={true}
        submitButtonText="Submit"
        onFormSuccess={mockOnFormSuccess}
        validationSchema={simpleSchema}
        renderFields={(form) => (
          <FormSelect<{ category: string }>
            form={form}
            name="category"
            label="Category"
            placeholder="Select a category"
          >
            {categoryOptions.map((option) => (
              <SelectItem key={option.key}>{option.label}</SelectItem>
            ))}
          </FormSelect>
        )}
      />,
    );

    // Open select and choose option
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Category/ }));
    });

    await act(async () => {
      fireEvent.click(screen.getByRole('option', { name: 'Development' }));
    });

    // Submit form
    await waitFor(() => {
      fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
    });

    // Wait for form processing
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 200));
    });

    expect(mockOnFormSuccess).toHaveBeenCalledWith(
      expect.objectContaining({ category: 'development' }),
    );
  });

  it('displays error styling when field is invalid', async () => {
    renderFormSelect(
      {
        showSubmitButton: true,
        submitButtonText: 'Submit',
      },
      {
        icon: IconUser,
      },
    );

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
    });

    const hiddenSelect = screen.getByDisplayValue('');
    expect(hiddenSelect).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByText('Category is required')).toBeInTheDocument();
  });

  it('handles disabled state', () => {
    renderFormSelect({}, { isDisabled: true });

    const hiddenSelect = screen.getByDisplayValue('');
    expect(hiddenSelect).toBeDisabled();
  });

  it('resets form values to initial state', async () => {
    const initialValues = { category: 'development', priority: 'low' };

    renderFormSelect({
      defaultValues: initialValues,
      showSubmitButton: true,
      submitButtonText: 'Submit',
      showResetButton: true,
      resetButtonText: 'Reset',
    });

    // Change selection
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Category/ }));
    });

    await act(async () => {
      fireEvent.click(screen.getByRole('option', { name: 'Testing' }));
    });

    // Reset form using the button text
    await act(async () => {
      fireEvent.click(screen.getByText('Reset'));
    });

    // Verify reset to initial value
    const categoryButton = screen.getByRole('button', { name: /Category/ });
    expect(categoryButton).toHaveTextContent('Development');
  });
});
