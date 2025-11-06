// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { IconCalculator } from '@tabler/icons-react';
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';

import FormNumberInput from '@/components/shared/ManagedForm/FormNumberInput';
import ManagedForm from '@/components/shared/ManagedForm/ManagedForm';

import userEvent from '@testing-library/user-event';
import { ZodType, z } from 'zod';

type SampleFormData = {
  count: number;
  price: number;
};

const sampleFormSchema: ZodType<SampleFormData> = z.object({
  count: z.number().min(1, 'Count must be at least 1'),
  price: z.number().min(0, 'Price must be non-negative'),
});

// Helper function to render FormNumberInput with common props
const renderFormNumberInput = (
  formProps: Partial<
    React.ComponentProps<typeof ManagedForm<SampleFormData>>
  > = {},
  inputProps: Partial<{
    name: keyof SampleFormData;
    label: string;
    placeholder: string;
    icon: React.ComponentType<any>;
    isDisabled: boolean;
    isReadOnly: boolean;
    step: number;
    className: string;
  }> = {},
) => {
  const defaultFormProps = {
    onFormSuccess: vi.fn(),
    validationSchema: sampleFormSchema,
    defaultValues: { count: 0, price: 0 },
  };

  return render(
    <ManagedForm<SampleFormData>
      {...defaultFormProps}
      {...formProps}
      renderFields={(form) => (
        <FormNumberInput
          form={form as any}
          name="count"
          label="Count"
          placeholder="Enter count"
          {...inputProps}
        />
      )}
    />,
  );
};

describe('FormNumberInput', () => {
  it('renders number input with label and placeholder', () => {
    renderFormNumberInput();

    expect(screen.getByLabelText('Count')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Enter count')).toBeInTheDocument();
  });

  it('renders number input with icon', () => {
    renderFormNumberInput({}, { icon: IconCalculator });

    expect(screen.getByLabelText('Count')).toBeInTheDocument();
    // Icon should be present in the DOM
    const iconElement = document.querySelector('svg');
    expect(iconElement).toBeInTheDocument();
  });

  it('handles number input and updates form value', async () => {
    const user = userEvent.setup();
    renderFormNumberInput();

    const input = screen.getByLabelText('Count') as HTMLInputElement;

    await user.clear(input);
    await user.type(input, '42');

    expect(input.value).toBe('42');
  });

  it('handles formatted numbers with commas', async () => {
    const user = userEvent.setup();
    renderFormNumberInput();

    const input = screen.getByLabelText('Count') as HTMLInputElement;

    await user.clear(input);
    await user.type(input, '1,234');

    // Blur to trigger parseFormattedNumber
    await user.tab();

    await waitFor(() => {
      expect(input.value).toBe('1,234');
    });
  });

  it('displays validation error when field is invalid', async () => {
    renderFormNumberInput(
      {
        showSubmitButton: true,
        submitButtonText: 'Submit',
        defaultValues: { count: -1, price: 0 },
      },
      { name: 'count' },
    );

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
    });

    expect(screen.getByText('Count must be at least 1')).toBeInTheDocument();
  });

  it('handles form submission with valid number', async () => {
    const mockOnFormSuccess = vi.fn();
    const user = userEvent.setup();

    // Use a simple schema with just one required field for testing
    const simpleSchema = z.object({
      count: z.number().min(1, 'Count must be at least 1'),
    });

    render(
      <ManagedForm<{ count: number }>
        defaultValues={{ count: 0 }}
        showSubmitButton={true}
        submitButtonText="Submit"
        onFormSuccess={mockOnFormSuccess}
        validationSchema={simpleSchema}
        renderFields={(form) => (
          <FormNumberInput
            form={form as any}
            name="count"
            label="Count"
            placeholder="Enter count"
          />
        )}
      />,
    );

    const input = screen.getByLabelText('Count') as HTMLInputElement;

    // Enter a valid number
    await user.clear(input);
    await user.type(input, '10');
    await user.tab(); // Trigger blur

    // Submit form
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
    });

    // Wait for form processing
    await waitFor(() => {
      expect(mockOnFormSuccess).toHaveBeenCalledWith(
        expect.objectContaining({ count: 10 }),
      );
    });
  });

  it('displays error styling when field is invalid', async () => {
    renderFormNumberInput(
      {
        showSubmitButton: true,
        submitButtonText: 'Submit',
        defaultValues: { count: -1, price: 0 },
      },
      {
        icon: IconCalculator,
        name: 'count',
      },
    );

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
    });

    const input = screen.getByLabelText('Count');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByText('Count must be at least 1')).toBeInTheDocument();
  });

  it('handles disabled state', () => {
    renderFormNumberInput({}, { isDisabled: true });

    const input = screen.getByLabelText('Count');
    expect(input).toBeDisabled();
  });

  it('handles readonly state with proper styling', () => {
    renderFormNumberInput({}, { isReadOnly: true });

    const input = screen.getByLabelText('Count');
    expect(input).toHaveAttribute('readonly');
  });

  it('handles empty input value correctly', async () => {
    const user = userEvent.setup();
    renderFormNumberInput();

    const input = screen.getByLabelText('Count') as HTMLInputElement;

    // Clear the input
    await user.clear(input);
    await user.tab(); // Trigger blur

    expect(input.value).toBe('');
  });

  it('handles invalid number input', async () => {
    const user = userEvent.setup();
    renderFormNumberInput();

    const input = screen.getByLabelText('Count') as HTMLInputElement;

    // Try to enter invalid characters (should be filtered by NumberInput)
    await user.clear(input);
    await user.type(input, 'abc');

    // NumberInput should prevent non-numeric input
    expect(input.value).toBe('');
  });

  it('handles decimal numbers', async () => {
    const user = userEvent.setup();

    // Create schema that allows decimals
    const decimalSchema = z.object({
      price: z.number().min(0, 'Price must be non-negative'),
    });

    render(
      <ManagedForm<{ price: number }>
        defaultValues={{ price: 0 }}
        validationSchema={decimalSchema}
        onFormSuccess={vi.fn()}
        renderFields={(form) => (
          <FormNumberInput
            form={form as any}
            name="price"
            label="Price"
            placeholder="Enter price"
          />
        )}
      />,
    );

    const input = screen.getByLabelText('Price') as HTMLInputElement;

    await user.clear(input);
    await user.type(input, '19.99');

    expect(input.value).toBe('19.99');
  });

  it('triggers onBlur correctly with setTimeout', async () => {
    const user = userEvent.setup();
    renderFormNumberInput();

    const input = screen.getByLabelText('Count') as HTMLInputElement;

    await user.clear(input);
    await user.type(input, '123');

    // Focus and then blur to trigger the handleBlur function
    await user.tab();

    // The component uses setTimeout in handleBlur, so we need to wait
    await waitFor(() => {
      expect(input.value).toBe('123');
    });
  });

  it('handles large numbers with comma formatting', async () => {
    const user = userEvent.setup();
    renderFormNumberInput();

    const input = screen.getByLabelText('Count') as HTMLInputElement;

    await user.clear(input);
    await user.type(input, '1,000,000');
    await user.tab(); // Trigger blur

    await waitFor(() => {
      expect(input.value).toBe('1,000,000');
    });
  });

  it('handles step increments when step prop is provided', () => {
    renderFormNumberInput({}, { step: 10 });

    const input = screen.getByLabelText('Count');
    expect(input).toHaveAttribute('step', '10');
  });

  it('applies custom className correctly', () => {
    const customClass = 'custom-test-class';
    renderFormNumberInput({}, { className: customClass });

    // Check that the component renders with the custom class somewhere in its tree
    const componentContainer = document.querySelector(`.${customClass}`);
    expect(componentContainer).toBeInTheDocument();
  });
});
