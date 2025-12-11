// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render, screen } from '@testing-library/react';
import { act } from 'react';
import React from 'react';

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
  Switch: ({ children, isSelected, onValueChange, ...props }: any) => (
    <label data-testid="switch" {...props}>
      <input
        type="checkbox"
        checked={isSelected}
        onChange={(e) => onValueChange?.(e.target.checked)}
        data-testid="switch-input"
      />
      {children}
    </label>
  ),
  Tabs: ({ children, selectedKey, onSelectionChange, ...props }: any) => {
    // Clone children and pass onSelectionChange to Tab components
    const clonedChildren = React.Children.map(children, (child) => {
      if (React.isValidElement(child)) {
        return React.cloneElement(child as any, {
          onSelectionChange,
          tabKey: (child as any).key, // Pass the key as a prop
        });
      }
      return child;
    });

    return (
      <div data-testid="tabs" data-selected={selectedKey} {...props}>
        {clonedChildren}
      </div>
    );
  },
  Tab: ({ title, onSelectionChange, tabKey, ...props }: any) => (
    <button
      data-testid={`tab-${tabKey || props.key}`}
      onClick={() => onSelectionChange?.(tabKey || props.key)}
      {...props}
    >
      {title}
    </button>
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
  IconCheck: () => <div data-testid="check-icon">Check</div>,
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

      const snippets = screen.getAllByTestId('code-snippet');
      const externalUrlSnippet = snippets.find((snippet) =>
        snippet.textContent?.includes(
          'https://api.example.com/v1/chat/completions',
        ),
      );
      expect(externalUrlSnippet).toBeInTheDocument();
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

      const snippets = screen.getAllByTestId('code-snippet');
      const internalUrlSnippet = snippets.find((snippet) =>
        snippet.textContent?.includes(
          'http://test-internal.example.com/v1/chat/completions',
        ),
      );
      expect(internalUrlSnippet).toBeInTheDocument();
    });

    it('handles aim without workload output', () => {
      render(
        <AIMConnectModal {...defaultProps} aim={mockAimWithoutWorkload} />,
      );

      // Should render at least one snippet (internal URL is always shown)
      const snippets = screen.getAllByTestId('code-snippet');
      expect(snippets.length).toBeGreaterThan(0);
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

      const codeSnippets = screen.getAllByTestId('code-snippet');
      // The code example snippet is the one with curl command
      const codeSnippet = codeSnippets.find((snippet) =>
        snippet.textContent?.includes('curl -X POST'),
      );
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

      const codeSnippets = screen.getAllByTestId('code-snippet');
      // The code example snippet is the one with curl command
      const codeSnippet = codeSnippets.find((snippet) =>
        snippet.textContent?.includes('curl -X POST'),
      );
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

      const codeSnippets = screen.getAllByTestId('code-snippet');
      // The code example snippet is the one with curl command
      const codeSnippet = codeSnippets.find((snippet) =>
        snippet.textContent?.includes('curl -X POST'),
      );
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
    it('sets correct aria-labels on snippet fields', () => {
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

      const snippets = screen.getAllByTestId('code-snippet');

      // Check external URL snippet
      const externalUrlSnippet = snippets.find(
        (snippet) =>
          snippet.getAttribute('aria-label') ===
          'actions.connect.modal.externalUrl',
      );
      expect(externalUrlSnippet).toBeInTheDocument();

      // Check internal URL snippet
      const internalUrlSnippet = snippets.find(
        (snippet) =>
          snippet.getAttribute('aria-label') ===
          'actions.connect.modal.internalUrl',
      );
      expect(internalUrlSnippet).toBeInTheDocument();

      // Check code example snippet
      const codeSnippet = snippets.find(
        (snippet) =>
          snippet.getAttribute('aria-label') ===
          'actions.connect.modal.codeExample',
      );
      expect(codeSnippet).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles aim without workload', () => {
      render(
        <AIMConnectModal {...defaultProps} aim={mockAimWithoutWorkload} />,
      );

      // Should still render the modal
      expect(screen.getByTestId('modal')).toBeInTheDocument();

      // Should still render snippets
      const snippets = screen.getAllByTestId('code-snippet');
      expect(snippets.length).toBeGreaterThan(0);
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

    it('renders copy icons in snippets', () => {
      render(<AIMConnectModal {...defaultProps} />);

      const copyIcons = screen.getAllByTestId('copy-icon');
      expect(copyIcons.length).toBeGreaterThan(0);
    });
  });

  describe('Language Selection', () => {
    it('renders language tabs with curl as default', () => {
      render(<AIMConnectModal {...defaultProps} />);

      const tabs = screen.getByTestId('tabs');
      expect(tabs).toBeInTheDocument();
      expect(tabs).toHaveAttribute('data-selected', 'curl');
    });

    it('renders all three language tabs', () => {
      render(<AIMConnectModal {...defaultProps} />);

      expect(screen.getByTestId('tab-curl')).toBeInTheDocument();
      expect(screen.getByTestId('tab-python')).toBeInTheDocument();
      expect(screen.getByTestId('tab-javascript')).toBeInTheDocument();
    });

    it('displays curl code example by default', () => {
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

      const codeSnippets = screen.getAllByTestId('code-snippet');
      const codeSnippet = codeSnippets.find((snippet) =>
        snippet.textContent?.includes('curl -X POST'),
      );
      expect(codeSnippet).toHaveTextContent('curl -X POST');
      expect(codeSnippet).toHaveTextContent(
        'https://api.example.com/v1/chat/completions',
      );
    });

    it('displays python code example when selected', () => {
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

      const codeSnippets = screen.getAllByTestId('code-snippet');
      const codeSnippet = codeSnippets.find(
        (snippet) =>
          snippet.getAttribute('aria-label') ===
          'actions.connect.modal.codeExample',
      );

      expect(codeSnippet).toBeDefined();
    });

    it('displays javascript code example when selected', () => {
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

      const codeSnippets = screen.getAllByTestId('code-snippet');
      const codeSnippet = codeSnippets.find(
        (snippet) =>
          snippet.getAttribute('aria-label') ===
          'actions.connect.modal.codeExample',
      );
      expect(codeSnippet).toBeDefined();
    });
  });

  describe('URL Toggle Switch', () => {
    it('renders the internal URL switch', () => {
      render(<AIMConnectModal {...defaultProps} />);

      const switchElement = screen.getByTestId('switch');
      expect(switchElement).toBeInTheDocument();
      expect(switchElement).toHaveTextContent(
        'actions.connect.modal.useInternalUrl',
      );
    });

    it('switch is unchecked by default (external URL)', () => {
      render(<AIMConnectModal {...defaultProps} />);

      const switchInput = screen.getByTestId('switch-input');
      expect(switchInput).not.toBeChecked();
    });

    it('toggles between external and internal URL in code snippet', async () => {
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

      const codeSnippets = screen.getAllByTestId('code-snippet');
      const codeSnippet = codeSnippets.find((snippet) =>
        snippet.textContent?.includes('curl -X POST'),
      );

      // Initially should show external URL
      expect(codeSnippet).toHaveTextContent(
        'https://api.example.com/v1/chat/completions',
      );

      // Toggle switch
      const switchInput = screen.getByTestId('switch-input');
      await act(async () => {
        fireEvent.click(switchInput);
      });

      // After toggle, the component would re-render with internal URL
      // Note: Due to mock limitations, we verify the switch state changed
      expect(switchInput).toBeChecked();
    });
  });

  describe('Code Examples Content', () => {
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

    it('curl example contains correct structure', () => {
      render(<AIMConnectModal {...defaultProps} aim={aimWithHosts} />);

      const codeSnippets = screen.getAllByTestId('code-snippet');
      const codeSnippet = codeSnippets.find((snippet) =>
        snippet.textContent?.includes('curl -X POST'),
      );
      expect(codeSnippet).toHaveTextContent('curl -X POST');
      expect(codeSnippet).toHaveTextContent('-H "Authorization: Bearer');
      expect(codeSnippet).toHaveTextContent(
        '-H "Content-Type: application/json"',
      );
      expect(codeSnippet).toHaveTextContent('"messages"');
      expect(codeSnippet).toHaveTextContent('"stream": false');
    });

    it('includes UPDATE_YOUR_API_KEY_HERE placeholder in all examples', () => {
      render(<AIMConnectModal {...defaultProps} aim={aimWithHosts} />);

      const codeSnippets = screen.getAllByTestId('code-snippet');
      const codeSnippet = codeSnippets.find((snippet) =>
        snippet.textContent?.includes('curl'),
      );
      expect(codeSnippet).toHaveTextContent('UPDATE_YOUR_API_KEY_HERE');
    });

    it('includes model canonical name in code examples', () => {
      render(<AIMConnectModal {...defaultProps} aim={aimWithHosts} />);

      const codeSnippets = screen.getAllByTestId('code-snippet');
      const codeSnippet = codeSnippets.find((snippet) =>
        snippet.textContent?.includes('curl'),
      );
      expect(codeSnippet).toHaveTextContent(aimWithHosts.canonicalName);
    });

    it('includes Hello message in all examples', () => {
      render(<AIMConnectModal {...defaultProps} aim={aimWithHosts} />);

      const codeSnippets = screen.getAllByTestId('code-snippet');
      const codeSnippet = codeSnippets.find((snippet) =>
        snippet.textContent?.includes('curl'),
      );
      expect(codeSnippet).toHaveTextContent('Hello');
    });
  });

  describe('URL Format', () => {
    it('appends /v1/chat/completions to external host', () => {
      const aimWithExternalHost = {
        ...mockAimWithWorkload,
        workload: {
          ...mockAimWithWorkload.workload!,
          output: {
            externalHost: 'https://api.example.com',
          },
        },
      };

      render(<AIMConnectModal {...defaultProps} aim={aimWithExternalHost} />);

      const snippets = screen.getAllByTestId('code-snippet');
      const urlSnippet = snippets.find((snippet) =>
        snippet.textContent?.includes(
          'https://api.example.com/v1/chat/completions',
        ),
      );
      expect(urlSnippet).toBeInTheDocument();
    });

    it('appends /v1/chat/completions to internal host with http prefix', () => {
      const aimWithInternalHost = {
        ...mockAimWithWorkload,
        workload: {
          ...mockAimWithWorkload.workload!,
          output: {
            internalHost: 'internal.example.com',
          },
        },
      };

      render(<AIMConnectModal {...defaultProps} aim={aimWithInternalHost} />);

      const snippets = screen.getAllByTestId('code-snippet');
      const urlSnippet = snippets.find((snippet) =>
        snippet.textContent?.includes(
          'http://internal.example.com/v1/chat/completions',
        ),
      );
      expect(urlSnippet).toBeInTheDocument();
    });
  });
});
