// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { IconUser } from '@tabler/icons-react';
import { act, fireEvent, render, screen } from '@testing-library/react';

import FormInput from '@/components/shared/ManagedForm/FormInput';
import ManagedForm from '@/components/shared/ManagedForm/ManagedForm';

import { ZodType, z } from 'zod';

type SampleFormData = {
  username: string;
  email: string;
};

const sampleFormSchema: ZodType<SampleFormData> = z.object({
  username: z.string().nonempty('Username is required'),
  email: z.string().email('Invalid email format'),
});

// Helper function to render FormInput with common props
const renderFormInput = (
  formProps: Partial<
    React.ComponentProps<typeof ManagedForm<SampleFormData>>
  > = {},
  inputProps: Partial<
    React.ComponentProps<typeof FormInput<SampleFormData>>
  > = {},
) => {
  const defaultFormProps = {
    onFormSuccess: vi.fn(),
    validationSchema: sampleFormSchema,
    defaultValues: { username: '', email: '' },
  };

  return render(
    <ManagedForm<SampleFormData>
      {...defaultFormProps}
      {...formProps}
      renderFields={(form) => (
        <FormInput<SampleFormData>
          form={form}
          name="username"
          label="Username"
          placeholder="Enter your username"
          {...inputProps}
        />
      )}
    />,
  );
};

describe('FormInput', () => {
  it('renders input with label and placeholder', () => {
    renderFormInput();

    expect(screen.getByLabelText('Username')).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText('Enter your username'),
    ).toBeInTheDocument();
  });

  it('renders input with icon', () => {
    renderFormInput({}, { icon: IconUser });

    const input = screen.getByLabelText('Username');
    expect(input).toBeInTheDocument();

    // Check if icon is rendered (the icon should be in the DOM)
    const iconElement = document.querySelector('svg');
    expect(iconElement).toBeInTheDocument();
  });

  it('displays validation error when required field is empty', async () => {
    renderFormInput({
      showSubmitButton: true,
      submitButtonText: 'Submit',
    });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
    });

    expect(screen.getByText('Username is required')).toBeInTheDocument();
  });

  it('displays validation error for invalid email format', async () => {
    const emailFormSchema = z.object({
      email: z.string().email('Invalid email format'),
    });

    render(
      <ManagedForm<{ email: string }>
        defaultValues={{ email: '' }}
        showSubmitButton={true}
        submitButtonText="Submit"
        onFormSuccess={vi.fn()}
        validationSchema={emailFormSchema}
        renderFields={(form) => (
          <FormInput<{ email: string }>
            form={form}
            name="email"
            label="Email"
            placeholder="Enter your email"
            type="email"
          />
        )}
      />,
    );

    const emailInput = screen.getByLabelText('Email');

    await act(async () => {
      fireEvent.change(emailInput, { target: { value: 'invalid-email' } });
    });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
    });

    expect(screen.getByText('Invalid email format')).toBeInTheDocument();
  });

  it('handles user input and form submission', async () => {
    const mockOnFormSuccess = vi.fn();

    // Use a simple schema with just one required field for testing
    const simpleSchema = z.object({
      username: z.string().nonempty('Username is required'),
    });

    render(
      <ManagedForm<{ username: string }>
        defaultValues={{ username: '' }}
        showSubmitButton={true}
        submitButtonText="Submit"
        onFormSuccess={mockOnFormSuccess}
        validationSchema={simpleSchema}
        renderFields={(form) => (
          <FormInput<{ username: string }>
            form={form}
            name="username"
            label="Username"
            placeholder="Enter your username"
          />
        )}
      />,
    );

    const usernameInput = screen.getByLabelText('Username');

    // Type in the input
    await act(async () => {
      fireEvent.change(usernameInput, { target: { value: 'testuser' } });
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
      expect.objectContaining({ username: 'testuser' }),
    );
  });

  it('displays error styling when field is invalid', async () => {
    renderFormInput(
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

    const input = screen.getByLabelText('Username');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByText('Username is required')).toBeInTheDocument();

    // Check if icon has error styling
    const iconElement = document.querySelector('svg');
    expect(iconElement).toHaveClass('stroke-danger');
  });

  it('applies correct icon styling for valid state', () => {
    renderFormInput({}, { icon: IconUser });

    const iconElement = document.querySelector('svg');
    expect(iconElement).toHaveClass('stroke-neutral-500');
    expect(iconElement).not.toHaveClass('stroke-danger');
  });

  it('handles disabled state', () => {
    renderFormInput({}, { isDisabled: true });

    const input = screen.getByLabelText('Username');
    expect(input).toBeDisabled();
  });

  it('handles read-only state with correct styling', () => {
    renderFormInput({}, { isReadOnly: true });

    const input = screen.getByLabelText('Username');
    expect(input).toHaveAttribute('readonly');

    // Check that the read-only styling classes are applied to the component
    const componentWithReadOnlyStyles = document.querySelector(
      '[class*="text-opacity-disabled"]',
    );
    expect(componentWithReadOnlyStyles).toBeInTheDocument();

    const componentWithForegroundStyles = document.querySelector(
      '[class*="text-foreground"]',
    );
    expect(componentWithForegroundStyles).toBeInTheDocument();
  });

  it('resets form values to initial state', async () => {
    const initialValues = {
      username: 'initialuser',
      email: 'initial@test.com',
    };

    renderFormInput({
      defaultValues: initialValues,
      showSubmitButton: true,
      submitButtonText: 'Submit',
      showResetButton: true,
      resetButtonText: 'Reset',
    });

    const usernameInput = screen.getByLabelText('Username');

    // Change input value
    await act(async () => {
      fireEvent.change(usernameInput, { target: { value: 'changeduser' } });
    });

    expect(usernameInput).toHaveValue('changeduser');

    // Reset form using the button
    await act(async () => {
      fireEvent.click(screen.getByText('Reset'));
    });

    // Verify reset to initial value
    expect(usernameInput).toHaveValue('initialuser');
  });

  it('applies custom className correctly', () => {
    const customClass = 'custom-input-class';
    renderFormInput({}, { className: customClass });

    // Check that the component renders with the custom class somewhere in its tree
    const componentContainer = document.querySelector(`.${customClass}`);
    expect(componentContainer).toBeInTheDocument();
  });

  it('handles different input types', () => {
    const passwordSchema = z.object({
      password: z.string().min(6, 'Password must be at least 6 characters'),
    });

    render(
      <ManagedForm<{ password: string }>
        defaultValues={{ password: '' }}
        onFormSuccess={vi.fn()}
        validationSchema={passwordSchema}
        renderFields={(form) => (
          <FormInput<{ password: string }>
            form={form}
            name="password"
            label="Password"
            type="password"
            placeholder="Enter your password"
          />
        )}
      />,
    );

    const passwordInput = screen.getByLabelText('Password');
    expect(passwordInput).toHaveAttribute('type', 'password');
  });

  it('validates input constraints correctly', async () => {
    const constrainedSchema = z.object({
      username: z
        .string()
        .min(3, 'Username must be at least 3 characters')
        .max(10, 'Username must be at most 10 characters'),
    });

    render(
      <ManagedForm<{ username: string }>
        defaultValues={{ username: '' }}
        showSubmitButton={true}
        submitButtonText="Submit"
        onFormSuccess={vi.fn()}
        validationSchema={constrainedSchema}
        renderFields={(form) => (
          <FormInput<{ username: string }>
            form={form}
            name="username"
            label="Username"
            placeholder="Enter your username"
          />
        )}
      />,
    );

    const usernameInput = screen.getByLabelText('Username');

    // Test minimum length validation
    await act(async () => {
      fireEvent.change(usernameInput, { target: { value: 'ab' } });
    });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
    });

    expect(
      screen.getByText('Username must be at least 3 characters'),
    ).toBeInTheDocument();

    // Test maximum length validation
    await act(async () => {
      fireEvent.change(usernameInput, {
        target: { value: 'verylongusername' },
      });
    });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
    });

    expect(
      screen.getByText('Username must be at most 10 characters'),
    ).toBeInTheDocument();
  });

  it('clears error message when input becomes valid', async () => {
    renderFormInput({
      showSubmitButton: true,
      submitButtonText: 'Submit',
    });

    // First, trigger validation error
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
    });

    expect(screen.getByText('Username is required')).toBeInTheDocument();

    // Then, provide valid input
    const usernameInput = screen.getByLabelText('Username');
    await act(async () => {
      fireEvent.change(usernameInput, { target: { value: 'validuser' } });
    });

    // Error message should be cleared
    expect(screen.queryByText('Username is required')).not.toBeInTheDocument();
  });
});
