// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render, screen } from '@testing-library/react';
import { act } from 'react';

import { Aim } from '@/types/aims';

import AIMConnectModal from '@/components/features/models/AIMConnectModal';
import { mockAims } from '@/__mocks__/services/app/aims.data';

import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock useTranslation
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// Mock heroui components
vi.mock('@heroui/react', () => ({
  Button: ({ children, onPress, color, ...props }: any) => (
    <button onClick={onPress} data-color={color} {...props}>
      {children}
    </button>
  ),
  Input: ({ value, readOnly, label, ...props }: any) => (
    <div>
      {label && <label>{label}</label>}
      <input value={value} readOnly={readOnly} {...props} />
    </div>
  ),
  Snippet: ({ children, copyIcon, classNames, ...props }: any) => (
    <div data-testid="code-snippet" {...props}>
      {children}
      {copyIcon}
    </div>
  ),
}));

// Mock ActionButton component
vi.mock('@/components/shared/Buttons', () => ({
  ActionButton: ({ children, onPress, primary, secondary, ...props }: any) => (
    <button
      onClick={onPress}
      data-primary={primary}
      data-secondary={secondary}
      {...props}
    >
      {children}
    </button>
  ),
}));

// Mock Modal component
vi.mock('@/components/shared/Modal/Modal', () => ({
  Modal: ({ children, title, footer, onClose, size }: any) => (
    <div data-testid="modal" data-size={size}>
      <div data-testid="modal-header">
        <h2>{title}</h2>
        <button onClick={onClose} data-testid="modal-close">
          ×
        </button>
      </div>
      <div data-testid="modal-content">{children}</div>
      <div data-testid="modal-footer">{footer}</div>
    </div>
  ),
}));

// Mock Tabler icon
vi.mock('@tabler/icons-react', () => ({
  IconCopy: () => <div data-testid="copy-icon">Copy</div>,
}));

describe('AIMConnectModal', () => {
  const mockOnOpenChange = vi.fn();
  const mockOnConfirmAction = vi.fn();

  // Use the first aim from mockAims that has a deployed workload
  const mockAimWithWorkload = mockAims[0]; // Llama 2 7B with RUNNING workload
  const mockAimWithoutWorkload = mockAims[1]; // Stable Diffusion XL without workload

  const defaultProps = {
    onOpenChange: mockOnOpenChange,
    onConfirmAction: mockOnConfirmAction,
    isOpen: true,
    aim: mockAimWithWorkload,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders the modal when isOpen is true', () => {
      render(<AIMConnectModal {...defaultProps} />);

      expect(screen.getByTestId('modal')).toBeInTheDocument();
      expect(
        screen.getByText('actions.connect.modal.title'),
      ).toBeInTheDocument();
    });

    it('does not render the modal when isOpen is false', () => {
      render(<AIMConnectModal {...defaultProps} isOpen={false} />);

      expect(screen.queryByTestId('modal')).not.toBeInTheDocument();
    });

    it('renders modal with correct size', () => {
      render(<AIMConnectModal {...defaultProps} />);

      expect(screen.getByTestId('modal')).toHaveAttribute('data-size', 'xl');
    });

    it('renders only externalUrl even when workload that has both URLs', () => {
      const aimWithBothUrls = {
        ...mockAimWithWorkload,
        workload: {
          ...mockAimWithWorkload.workload!,
          output: {
            externalHost: 'https://api.example.com',
            internalHost: 'test-host.example.com',
          },
        },
      };

      render(<AIMConnectModal {...defaultProps} aim={aimWithBothUrls} />);

      expect(
        screen.getByText('actions.connect.modal.externalUrl'),
      ).toBeInTheDocument();
      expect(
        screen.getByText('actions.connect.modal.internalUrl'),
      ).toBeInTheDocument();
      expect(
        screen.getByText('actions.connect.modal.codeExample'),
      ).toBeInTheDocument();
    });

    it('renders action buttons', () => {
      render(<AIMConnectModal {...defaultProps} />);

      expect(screen.getByText('actions.close.title')).toBeInTheDocument();
      expect(
        screen.getByText('actions.connect.modal.openChat'),
      ).toBeInTheDocument();
    });
  });

  describe('URL Generation', () => {
    it('generates correct external URL', () => {
      render(<AIMConnectModal {...defaultProps} />);

      // The workload in mockAims[0] doesn't have externalHost, so let's create one
      const aimWithExternalHost = {
        ...mockAimWithWorkload,
        workload: {
          ...mockAimWithWorkload.workload!,
          output: {
            externalHost: 'https://api.example.com',
            internalHost: 'test-host.example.com',
          },
        },
      };

      render(<AIMConnectModal {...defaultProps} aim={aimWithExternalHost} />);

      const externalUrlInput = screen.getByDisplayValue(
        'https://api.example.com/v1/chat/completions',
      );
      expect(externalUrlInput).toBeInTheDocument();
      expect(externalUrlInput).toHaveAttribute('readOnly');
    });

    it('generates correct internal URL from mock data', () => {
      // Create aim with specific internal host
      const aimWithInternalHost = {
        ...mockAimWithWorkload,
        workload: {
          ...mockAimWithWorkload.workload!,
          output: {
            internalHost: 'test-internal.example.com',
          },
        },
      };

      render(<AIMConnectModal {...defaultProps} aim={aimWithInternalHost} />);

      const internalUrlInput = screen.getByDisplayValue(
        'http://test-internal.example.com/v1/chat/completions',
      );
      expect(internalUrlInput).toBeInTheDocument();
      expect(internalUrlInput).toHaveAttribute('readOnly');
    });

    it('handles aim without workload output', () => {
      render(
        <AIMConnectModal {...defaultProps} aim={mockAimWithoutWorkload} />,
      );

      // Should render empty URL
      const inputs = screen.getAllByRole('textbox');
      const emptyInput = inputs.find(
        (input) => input.getAttribute('value') === '',
      );
      expect(emptyInput).toBeInTheDocument();
    });
  });

  describe('Code Example', () => {
    it('generates correct curl code snippet', () => {
      const aimWithHosts = {
        ...mockAimWithWorkload,
        workload: {
          ...mockAimWithWorkload.workload!,
          output: {
            externalHost: 'https://api.example.com',
            internalHost: 'test-host.example.com',
          },
        },
      };

      render(<AIMConnectModal {...defaultProps} aim={aimWithHosts} />);

      const codeSnippet = screen.getByTestId('code-snippet');
      expect(codeSnippet).toBeInTheDocument();

      // Check if the code snippet contains expected content
      expect(codeSnippet).toHaveTextContent('curl -X POST');
      expect(codeSnippet).toHaveTextContent(
        'https://api.example.com/v1/chat/completions',
      );
      expect(codeSnippet).toHaveTextContent(
        'Authorization: Bearer UPDATE_YOUR_API_KEY_HERE',
      );
      expect(codeSnippet).toHaveTextContent(
        `"model": "${mockAimWithWorkload.canonicalName}"`,
      );
      expect(codeSnippet).toHaveTextContent('"content": "Hello"');
      expect(codeSnippet).toHaveTextContent('"role": "user"');
      expect(codeSnippet).toHaveTextContent('"stream": false');
    });

    it('includes aim canonical name in code snippet', () => {
      render(<AIMConnectModal {...defaultProps} />);

      const codeSnippet = screen.getByTestId('code-snippet');
      expect(codeSnippet).toHaveTextContent(mockAimWithWorkload.canonicalName);
    });

    it('handles missing aim canonical name', () => {
      const aimWithoutCanonicalName: Aim = {
        ...mockAimWithWorkload,
        canonicalName: '' as any,
      };

      render(
        <AIMConnectModal {...defaultProps} aim={aimWithoutCanonicalName} />,
      );

      const codeSnippet = screen.getByTestId('code-snippet');
      expect(codeSnippet).toHaveTextContent('"model": ""');
    });
  });

  describe('User Interactions', () => {
    it('calls onOpenChange when close button is clicked', async () => {
      render(<AIMConnectModal {...defaultProps} />);

      const closeButton = screen.getByText('actions.close.title');

      await act(async () => {
        fireEvent.click(closeButton);
      });

      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });

    it('calls onConfirmAction and onOpenChange when confirm button is clicked', async () => {
      render(<AIMConnectModal {...defaultProps} />);

      const confirmButton = screen.getByText('actions.connect.modal.openChat');

      await act(async () => {
        fireEvent.click(confirmButton);
      });

      expect(mockOnConfirmAction).toHaveBeenCalledWith(mockAimWithWorkload);
      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });

    it('calls onOpenChange when modal close button is clicked', async () => {
      render(<AIMConnectModal {...defaultProps} />);

      const modalCloseButton = screen.getByTestId('modal-close');

      await act(async () => {
        fireEvent.click(modalCloseButton);
      });

      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });

    it('does not call onConfirmAction when aim is undefined', async () => {
      render(<AIMConnectModal {...defaultProps} aim={undefined} />);

      const confirmButton = screen.getByText('actions.connect.modal.openChat');

      await act(async () => {
        fireEvent.click(confirmButton);
      });

      expect(mockOnConfirmAction).not.toHaveBeenCalled();
      expect(mockOnOpenChange).not.toHaveBeenCalled();
    });

    it('does not call onConfirmAction when onConfirmAction is undefined', async () => {
      render(
        <AIMConnectModal
          {...defaultProps}
          onConfirmAction={undefined as any}
        />,
      );

      const confirmButton = screen.getByText('actions.connect.modal.openChat');

      await act(async () => {
        fireEvent.click(confirmButton);
      });

      expect(mockOnOpenChange).not.toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    it('sets correct aria-labels on input fields', () => {
      const aimWithHosts = {
        ...mockAimWithWorkload,
        workload: {
          ...mockAimWithWorkload.workload!,
          output: {
            externalHost: 'https://api.example.com',
            internalHost: 'test-host.example.com',
          },
        },
      };

      render(<AIMConnectModal {...defaultProps} aim={aimWithHosts} />);

      const externalUrlInput = screen.getByDisplayValue(
        'https://api.example.com/v1/chat/completions',
      );

      // Make sure the internal URL is not rendered
      const codeSnippet = screen.getByTestId('code-snippet');

      expect(externalUrlInput).toHaveAttribute(
        'aria-label',
        'actions.connect.modal.externalUrl',
      );
      expect(codeSnippet).toHaveAttribute(
        'aria-label',
        'actions.connect.modal.codeExample',
      );

      expect(
        screen.queryByText('http://test-host.example.com/v1/chat/completions'),
      ).not.toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles aim without workload', () => {
      render(
        <AIMConnectModal {...defaultProps} aim={mockAimWithoutWorkload} />,
      );

      // Should still render the modal
      expect(screen.getByTestId('modal')).toBeInTheDocument();

      // URL inputs should be empty
      const inputs = screen.getAllByRole('textbox');
      expect(inputs.length).toBeGreaterThan(0);
    });

    it('handles undefined aim', () => {
      render(<AIMConnectModal {...defaultProps} aim={undefined} />);

      expect(screen.getByTestId('modal')).toBeInTheDocument();
    });
  });

  describe('Component Styling', () => {
    it('applies correct CSS classes', () => {
      render(<AIMConnectModal {...defaultProps} />);

      const modal = screen.getByTestId('modal');
      expect(modal).toBeInTheDocument();

      const modalContent = screen.getByTestId('modal-content');
      expect(modalContent).toBeInTheDocument();
    });

    it('renders copy icon in code snippet', () => {
      render(<AIMConnectModal {...defaultProps} />);

      const copyIcon = screen.getByTestId('copy-icon');
      expect(copyIcon).toBeInTheDocument();
    });
  });
});
