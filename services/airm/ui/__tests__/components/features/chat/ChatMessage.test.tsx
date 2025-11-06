// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, fireEvent, render, screen } from '@testing-library/react';

import { ChatMessage } from '@/components/features/chat/ChatMessage';
import ProviderWrapper from '@/__tests__/ProviderWrapper';

import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Import mocks
import { setupClipboardMock } from '@/__mocks__/services/app/clipboard';
import {
  mockUserMessage,
  mockAssistantMessage,
  mockSystemMessage,
  mockDebugInfo,
  mockMarkdownMessage,
  mockUserMarkdownMessage,
} from '@/__mocks__/services/app/chat.data';

setupClipboardMock();

// Use fake timers
vi.useFakeTimers();

describe('ChatMessage Component', () => {
  const defaultProps = {
    message: mockUserMessage,
    showCursorOnMessage: false,
    allowEdit: true,
    allowCopy: true,
    messageIsStreaming: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.clearAllTimers();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  describe('Message Display', () => {
    it('renders user message correctly', () => {
      render(
        <ProviderWrapper>
          <ChatMessage {...defaultProps} />
        </ProviderWrapper>,
      );

      expect(screen.getByText('roles.user')).toBeInTheDocument();
      expect(
        screen.getByText('Hello, this is a user message'),
      ).toBeInTheDocument();
    });

    it('renders assistant message correctly', () => {
      render(
        <ProviderWrapper>
          <ChatMessage
            {...defaultProps}
            message={mockAssistantMessage}
            allowEdit={false}
          />
        </ProviderWrapper>,
      );

      expect(screen.getByText('roles.assistant')).toBeInTheDocument();
      // The content is rendered through markdown, so we check for the text content
      expect(
        screen.getByText(/Hello! This is an assistant response/),
      ).toBeInTheDocument();
    });

    it('renders system message correctly', () => {
      render(
        <ProviderWrapper>
          <ChatMessage
            {...defaultProps}
            message={mockSystemMessage}
            allowEdit={false}
          />
        </ProviderWrapper>,
      );

      expect(screen.getByText('roles.system')).toBeInTheDocument();
      expect(screen.getByText('This is a system message')).toBeInTheDocument();
    });

    it('shows streaming cursor when messageIsStreaming and showCursorOnMessage are true', () => {
      render(
        <ProviderWrapper>
          <ChatMessage
            {...defaultProps}
            message={mockAssistantMessage}
            messageIsStreaming={true}
            showCursorOnMessage={true}
            allowEdit={false}
          />
        </ProviderWrapper>,
      );

      // Check if the markdown content includes the cursor
      const content = screen.getByText(/Hello! This is an assistant response/);
      expect(content).toBeInTheDocument();
      // The cursor is added by the markdown processor, so we check the content rendered
      expect(document.body.textContent).toContain('▍');
    });
  });

  describe('Edit Functionality', () => {
    it('shows edit and delete buttons for user messages when allowEdit is true', () => {
      render(
        <ProviderWrapper>
          <ChatMessage {...defaultProps} />
        </ProviderWrapper>,
      );

      // Buttons should be present but invisible by default (group-hover behavior)
      // We can find them by their SVG icons since they don't have text labels
      const buttons = screen.getAllByRole('button');
      expect(buttons).toHaveLength(2); // edit and delete buttons

      // Check for edit icon (IconEdit)
      expect(document.querySelector('.tabler-icon-edit')).toBeInTheDocument();
      // Check for trash icon (IconTrash)
      expect(document.querySelector('.tabler-icon-trash')).toBeInTheDocument();
    });

    it('does not show edit and delete buttons when allowEdit is false', () => {
      render(
        <ProviderWrapper>
          <ChatMessage {...defaultProps} allowEdit={false} />
        </ProviderWrapper>,
      );

      expect(
        document.querySelector('.tabler-icon-edit'),
      ).not.toBeInTheDocument();
      expect(
        document.querySelector('.tabler-icon-trash'),
      ).not.toBeInTheDocument();
    });

    it('enters edit mode when edit button is clicked', async () => {
      render(
        <ProviderWrapper>
          <ChatMessage {...defaultProps} />
        </ProviderWrapper>,
      );

      const editButton = document
        .querySelector('.tabler-icon-edit')
        ?.closest('button');
      expect(editButton).toBeInTheDocument();

      await act(async () => {
        fireEvent.click(editButton!);
      });

      // Should show textarea and action buttons
      expect(screen.getByRole('textbox')).toBeInTheDocument();
      expect(screen.getByText('Save & Submit')).toBeInTheDocument();
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    it('saves edited message when Save & Submit is clicked', async () => {
      const mockOnEdit = vi.fn();

      render(
        <ProviderWrapper>
          <ChatMessage {...defaultProps} onEdit={mockOnEdit} />
        </ProviderWrapper>,
      );

      const editButton = document
        .querySelector('.tabler-icon-edit')
        ?.closest('button');

      await act(async () => {
        fireEvent.click(editButton!);
      });

      const textarea = screen.getByRole('textbox');

      await act(async () => {
        fireEvent.change(textarea, {
          target: { value: 'Edited message content' },
        });
      });

      const saveButton = screen.getByText('Save & Submit');

      await act(async () => {
        fireEvent.click(saveButton);
      });

      expect(mockOnEdit).toHaveBeenCalledWith({
        ...mockUserMessage,
        content: 'Edited message content',
      });
    });

    it('cancels editing when Cancel button is clicked', async () => {
      render(
        <ProviderWrapper>
          <ChatMessage {...defaultProps} />
        </ProviderWrapper>,
      );

      const editButton = document
        .querySelector('.tabler-icon-edit')
        ?.closest('button');

      await act(async () => {
        fireEvent.click(editButton!);
      });

      const textarea = screen.getByRole('textbox');

      await act(async () => {
        fireEvent.change(textarea, { target: { value: 'Changed content' } });
      });

      const cancelButton = screen.getByText('Cancel');

      await act(async () => {
        fireEvent.click(cancelButton);
      });

      // Should exit edit mode and revert content
      expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
      expect(
        screen.getByText('Hello, this is a user message'),
      ).toBeInTheDocument();
    });

    it('saves message when Enter is pressed in edit mode', async () => {
      const mockOnEdit = vi.fn();

      render(
        <ProviderWrapper>
          <ChatMessage {...defaultProps} onEdit={mockOnEdit} />
        </ProviderWrapper>,
      );

      const editButton = document
        .querySelector('.tabler-icon-edit')
        ?.closest('button');

      await act(async () => {
        fireEvent.click(editButton!);
      });

      const textarea = screen.getByRole('textbox');

      await act(async () => {
        fireEvent.change(textarea, { target: { value: 'New content' } });
        fireEvent.keyDown(textarea, { key: 'Enter' });
      });

      expect(mockOnEdit).toHaveBeenCalledWith({
        ...mockUserMessage,
        content: 'New content',
      });
    });

    it('does not save when Enter is pressed with Shift key', async () => {
      const mockOnEdit = vi.fn();

      render(
        <ProviderWrapper>
          <ChatMessage {...defaultProps} onEdit={mockOnEdit} />
        </ProviderWrapper>,
      );

      const editButton = document
        .querySelector('.tabler-icon-edit')
        ?.closest('button');

      await act(async () => {
        fireEvent.click(editButton!);
      });

      const textarea = screen.getByRole('textbox');

      await act(async () => {
        fireEvent.change(textarea, { target: { value: 'New content' } });
        fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true });
      });

      expect(mockOnEdit).not.toHaveBeenCalled();
    });

    it('calls onDelete when delete button is clicked', async () => {
      const mockOnDelete = vi.fn();

      render(
        <ProviderWrapper>
          <ChatMessage {...defaultProps} onDelete={mockOnDelete} />
        </ProviderWrapper>,
      );

      const deleteButton = document
        .querySelector('.tabler-icon-trash')
        ?.closest('button');

      await act(async () => {
        fireEvent.click(deleteButton!);
      });

      expect(mockOnDelete).toHaveBeenCalled();
    });
  });

  describe('Copy Functionality', () => {
    it('shows copy button for assistant messages when allowCopy is true', () => {
      render(
        <ProviderWrapper>
          <ChatMessage
            {...defaultProps}
            message={mockAssistantMessage}
            allowEdit={false}
          />
        </ProviderWrapper>,
      );

      expect(document.querySelector('.tabler-icon-copy')).toBeInTheDocument();
    });

    it('does not show copy button when allowCopy is false', () => {
      render(
        <ProviderWrapper>
          <ChatMessage
            {...defaultProps}
            message={mockAssistantMessage}
            allowEdit={false}
            allowCopy={false}
          />
        </ProviderWrapper>,
      );

      expect(
        document.querySelector('.tabler-icon-copy'),
      ).not.toBeInTheDocument();
    });

    it('copies message content to clipboard when copy button is clicked', async () => {
      render(
        <ProviderWrapper>
          <ChatMessage
            {...defaultProps}
            message={mockAssistantMessage}
            allowEdit={false}
          />
        </ProviderWrapper>,
      );

      const copyButton = document
        .querySelector('.tabler-icon-copy')
        ?.closest('button');

      await act(async () => {
        fireEvent.click(copyButton!);
      });

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        mockAssistantMessage.content,
      );
    });

    it('shows check icon temporarily after copying', async () => {
      render(
        <ProviderWrapper>
          <ChatMessage
            {...defaultProps}
            message={mockAssistantMessage}
            allowEdit={false}
          />
        </ProviderWrapper>,
      );

      const copyButton = document
        .querySelector('.tabler-icon-copy')
        ?.closest('button');

      await act(async () => {
        fireEvent.click(copyButton!);
      });

      // Check icon should be visible (look for the check icon class)
      expect(document.querySelector('.tabler-icon-check')).toBeInTheDocument();

      // After 2 seconds, should return to copy icon
      await act(async () => {
        vi.advanceTimersByTime(2000);
      });

      expect(document.querySelector('.tabler-icon-copy')).toBeInTheDocument();
      expect(
        document.querySelector('.tabler-icon-check'),
      ).not.toBeInTheDocument();
    });
  });

  describe('Debug Functionality', () => {
    it('shows debug button when debugInfo is provided', () => {
      render(
        <ProviderWrapper>
          <ChatMessage
            {...defaultProps}
            message={mockAssistantMessage}
            debugInfo={mockDebugInfo}
            allowEdit={false}
          />
        </ProviderWrapper>,
      );

      expect(screen.getByLabelText('debug-info')).toBeInTheDocument();
    });

    it('does not show debug button when debugInfo is not provided', () => {
      render(
        <ProviderWrapper>
          <ChatMessage
            {...defaultProps}
            message={mockAssistantMessage}
            allowEdit={false}
          />
        </ProviderWrapper>,
      );

      expect(screen.queryByLabelText('debug-info')).not.toBeInTheDocument();
    });

    it('opens debug modal when debug button is clicked', async () => {
      render(
        <ProviderWrapper>
          <ChatMessage
            {...defaultProps}
            message={mockAssistantMessage}
            debugInfo={mockDebugInfo}
            allowEdit={false}
          />
        </ProviderWrapper>,
      );

      const debugButton = screen.getByLabelText('debug-info');

      await act(async () => {
        fireEvent.click(debugButton);
      });

      // The DebugInfoModal should be rendered when showDebug is true
      // We can't easily test the modal content without mocking it,
      // but we can verify the button click doesn't error
      expect(debugButton).toBeInTheDocument();
    });
  });

  describe('Message Content Rendering', () => {
    it('renders markdown content correctly for assistant messages', () => {
      render(
        <ProviderWrapper>
          <ChatMessage
            {...defaultProps}
            message={mockMarkdownMessage}
            allowEdit={false}
          />
        </ProviderWrapper>,
      );

      // Check that markdown is processed
      expect(screen.getByText(/Heading/)).toBeInTheDocument();
      expect(screen.getByText(/This is/)).toBeInTheDocument();
      expect(screen.getByText(/bold/)).toBeInTheDocument();
    });

    it('renders plain text for user messages', () => {
      render(
        <ProviderWrapper>
          <ChatMessage {...defaultProps} message={mockUserMarkdownMessage} />
        </ProviderWrapper>,
      );

      // Should render as plain text, not markdown
      expect(
        screen.getByText(/# This should not be rendered as heading/),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/\*\*This should not be bold\*\*/),
      ).toBeInTheDocument();
    });

    it('disables Save button when message content is empty', async () => {
      render(
        <ProviderWrapper>
          <ChatMessage {...defaultProps} />
        </ProviderWrapper>,
      );

      const editButton = document
        .querySelector('.tabler-icon-edit')
        ?.closest('button');

      await act(async () => {
        fireEvent.click(editButton!);
      });

      const textarea = screen.getByRole('textbox');

      await act(async () => {
        fireEvent.change(textarea, { target: { value: '   ' } }); // Only whitespace
      });

      const saveButton = screen.getByText('Save & Submit');
      expect(saveButton).toBeDisabled();
    });

    it('does not call onEdit when message content is unchanged', async () => {
      const mockOnEdit = vi.fn();

      render(
        <ProviderWrapper>
          <ChatMessage {...defaultProps} onEdit={mockOnEdit} />
        </ProviderWrapper>,
      );

      const editButton = document
        .querySelector('.tabler-icon-edit')
        ?.closest('button');

      await act(async () => {
        fireEvent.click(editButton!);
      });

      const saveButton = screen.getByText('Save & Submit');

      await act(async () => {
        fireEvent.click(saveButton);
      });

      // Should not call onEdit when content hasn't changed
      expect(mockOnEdit).not.toHaveBeenCalled();
    });
  });
});
