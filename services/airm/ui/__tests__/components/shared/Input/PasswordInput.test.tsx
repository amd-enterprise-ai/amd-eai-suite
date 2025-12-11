// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';

import { PasswordInput } from '@/components/shared/Input/PasswordInput';

// Mock HeroUI components
vi.mock('@heroui/react', async () => {
  const actual = await vi.importActual('@heroui/react');
  return {
    ...actual,
    Input: ({ type, endContent, ...props }: any) => (
      <div data-testid="input-wrapper">
        <input data-testid="password-input" type={type} {...props} />
        {endContent && <div data-testid="end-content">{endContent}</div>}
      </div>
    ),
    Button: ({
      children,
      onPress,
      tabIndex,
      variant,
      isIconOnly,
      size,
      ...props
    }: any) => (
      <button
        data-testid="password-toggle-button"
        onClick={onPress}
        tabIndex={tabIndex}
        data-variant={variant}
        data-icon-only={isIconOnly}
        data-size={size}
        {...props}
      >
        {children}
      </button>
    ),
  };
});

// Mock icons
vi.mock('@tabler/icons-react', () => ({
  IconEye: (props: any) => (
    <svg data-testid="icon-eye" aria-label="Show password" {...props}>
      <title>Show password</title>
    </svg>
  ),
  IconEyeOff: (props: any) => (
    <svg data-testid="icon-eye-off" aria-label="Hide password" {...props}>
      <title>Hide password</title>
    </svg>
  ),
}));

describe('PasswordInput', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Basic rendering', () => {
    it('renders password input', () => {
      render(<PasswordInput />);
      expect(screen.getByTestId('password-input')).toBeInTheDocument();
    });

    it('renders with password type by default', () => {
      render(<PasswordInput />);
      const input = screen.getByTestId('password-input');
      expect(input).toHaveAttribute('type', 'password');
    });

    it('renders toggle button', () => {
      render(<PasswordInput />);
      expect(screen.getByTestId('password-toggle-button')).toBeInTheDocument();
    });

    it('renders eye icon by default (password hidden)', () => {
      render(<PasswordInput />);
      expect(screen.getByTestId('icon-eye')).toBeInTheDocument();
      expect(screen.queryByTestId('icon-eye-off')).not.toBeInTheDocument();
    });
  });

  describe('Password visibility toggle', () => {
    it('toggles to text type when button is clicked', () => {
      render(<PasswordInput />);
      const input = screen.getByTestId('password-input');
      const toggleButton = screen.getByTestId('password-toggle-button');

      expect(input).toHaveAttribute('type', 'password');
      expect(screen.getByTestId('icon-eye')).toBeInTheDocument();

      fireEvent.click(toggleButton);

      expect(input).toHaveAttribute('type', 'text');
      expect(screen.getByTestId('icon-eye-off')).toBeInTheDocument();
      expect(screen.queryByTestId('icon-eye')).not.toBeInTheDocument();
    });

    it('toggles back to password type when clicked again', () => {
      render(<PasswordInput />);
      const input = screen.getByTestId('password-input');
      const toggleButton = screen.getByTestId('password-toggle-button');

      // First click - reveal password
      fireEvent.click(toggleButton);
      expect(input).toHaveAttribute('type', 'text');
      expect(screen.getByTestId('icon-eye-off')).toBeInTheDocument();

      // Second click - hide password
      fireEvent.click(toggleButton);
      expect(input).toHaveAttribute('type', 'password');
      expect(screen.getByTestId('icon-eye')).toBeInTheDocument();
      expect(screen.queryByTestId('icon-eye-off')).not.toBeInTheDocument();
    });

    it('toggles multiple times correctly', () => {
      render(<PasswordInput />);
      const input = screen.getByTestId('password-input');
      const toggleButton = screen.getByTestId('password-toggle-button');

      // Toggle multiple times
      for (let i = 0; i < 5; i++) {
        fireEvent.click(toggleButton);
        expect(input).toHaveAttribute(
          'type',
          i % 2 === 0 ? 'text' : 'password',
        );
      }
    });
  });

  describe('Props forwarding', () => {
    it('forwards all props to Input component', () => {
      render(
        <PasswordInput
          name="password"
          placeholder="Enter password"
          label="Password"
          isRequired
        />,
      );

      const input = screen.getByTestId('password-input');
      expect(input).toHaveAttribute('name', 'password');
      expect(input).toHaveAttribute('placeholder', 'Enter password');
      expect(input).toHaveAttribute('label', 'Password');
    });

    it('applies custom className', () => {
      render(<PasswordInput className="custom-class" />);
      const input = screen.getByTestId('password-input');
      expect(input).toHaveClass('custom-class');
    });

    it('forwards value and onChange', () => {
      const handleChange = vi.fn();
      render(<PasswordInput value="test123" onChange={handleChange} />);

      const input = screen.getByTestId('password-input');
      expect(input).toHaveAttribute('value', 'test123');
    });
  });

  describe('Button behavior', () => {
    it('button has tabIndex -1 to prevent focus interference', () => {
      render(<PasswordInput />);
      const button = screen.getByTestId('password-toggle-button');
      expect(button).toHaveAttribute('tabIndex', '-1');
    });

    it('button uses light variant', () => {
      render(<PasswordInput />);
      const button = screen.getByTestId('password-toggle-button');
      expect(button).toHaveAttribute('data-variant', 'light');
    });

    it('button is icon only', () => {
      render(<PasswordInput />);
      const button = screen.getByTestId('password-toggle-button');
      expect(button).toHaveAttribute('data-icon-only', 'true');
    });

    it('button is size sm', () => {
      render(<PasswordInput />);
      const button = screen.getByTestId('password-toggle-button');
      expect(button).toHaveAttribute('data-size', 'sm');
    });
  });

  describe('Accessibility', () => {
    it('maintains input attributes for accessibility', () => {
      render(
        <PasswordInput
          label="Password"
          isRequired
          aria-label="Password input"
        />,
      );

      const input = screen.getByTestId('password-input');
      expect(input).toHaveAttribute('label', 'Password');
      expect(input).toHaveAttribute('aria-label', 'Password input');
    });

    it('button is keyboard accessible', () => {
      render(<PasswordInput />);
      const button = screen.getByTestId('password-toggle-button');
      expect(button.tagName).toBe('BUTTON');
    });
  });

  describe('Multiple instances', () => {
    it('each instance has independent reveal state', () => {
      const { container } = render(
        <div>
          <PasswordInput name="password1" />
          <PasswordInput name="password2" />
        </div>,
      );

      const inputs = container.querySelectorAll(
        'input[type="password"], input[type="text"]',
      );
      const toggleButtons = container.querySelectorAll('button[aria-label]');

      expect(inputs).toHaveLength(2);

      // Both start as password type
      expect(inputs[0]).toHaveAttribute('type', 'password');
      expect(inputs[1]).toHaveAttribute('type', 'password');

      // Toggle first one only
      fireEvent.click(toggleButtons[0]);

      // Re-query inputs after state change
      const updatedInputs = container.querySelectorAll(
        'input[type="password"], input[type="text"]',
      );
      expect(updatedInputs[0]).toHaveAttribute('type', 'text');
      expect(updatedInputs[1]).toHaveAttribute('type', 'password'); // Second unchanged
    });
  });
});
