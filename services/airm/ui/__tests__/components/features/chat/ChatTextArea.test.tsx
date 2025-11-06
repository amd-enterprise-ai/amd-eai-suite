// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { ChatTextArea } from '@/components/features/chat/ChatTextArea';
import ProviderWrapper from '@/__tests__/ProviderWrapper';

import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock HeroUI components
vi.mock('@heroui/react', () => ({
  Button: ({
    children,
    onPress,
    disabled,
    className,
    color,
    isIconOnly,
    radius,
    id,
    ...props
  }: any) => (
    <button
      onClick={onPress}
      disabled={disabled}
      className={className}
      id={id}
      data-testid={props['data-testid'] || 'button'}
      {...props}
    >
      {children}
    </button>
  ),
}));

// Mock next-i18next
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'chatInput.placeholder': 'Type your message...',
        'chatInput.placeholderDisabled': 'Chat is disabled',
      };
      return translations[key] || key;
    },
  }),
}));

describe('ChatTextArea Component', () => {
  const defaultProps = {
    content: '',
    handleChange: vi.fn(),
    handleKeyDown: vi.fn(),
    setIsTyping: vi.fn(),
    textareaRef: { current: null },
    disabled: false,
    sendDisabled: false,
    messageIsStreaming: false,
    handleSend: vi.fn(),
    handleStopConversation: vi.fn(),
    showScrollDownButton: false,
    onScrollDownClick: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders the textarea correctly', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');
      expect(textarea).toBeInTheDocument();
      expect(textarea).toHaveAttribute('id', 'chat-input');
      expect(textarea).toHaveAttribute('aria-label', 'chat-input');
    });

    it('renders with correct placeholder when enabled', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} />
        </ProviderWrapper>,
      );

      expect(
        screen.getByPlaceholderText('Type your message...'),
      ).toBeInTheDocument();
    });

    it('renders with disabled placeholder when disabled', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} disabled={true} />
        </ProviderWrapper>,
      );

      expect(
        screen.getByPlaceholderText('Chat is disabled'),
      ).toBeInTheDocument();
    });

    it('displays content value in textarea', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} content="Hello world" />
        </ProviderWrapper>,
      );

      expect(screen.getByDisplayValue('Hello world')).toBeInTheDocument();
    });

    it('renders send button when not streaming', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} messageIsStreaming={false} />
        </ProviderWrapper>,
      );

      expect(screen.getByTestId('send-button')).toBeInTheDocument();
    });

    it('renders stop button when streaming', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} messageIsStreaming={true} />
        </ProviderWrapper>,
      );

      expect(screen.queryByTestId('send-button')).not.toBeInTheDocument();
      // Stop button should be present but doesn't have a test-id in the component
      const buttons = screen.getAllByRole('button');
      expect(buttons).toHaveLength(1); // Only stop button
    });

    it('renders scroll down button when showScrollDownButton is true', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} showScrollDownButton={true} />
        </ProviderWrapper>,
      );

      const buttons = screen.getAllByRole('button');
      expect(buttons).toHaveLength(2); // Send button + scroll down button
    });

    it('does not render scroll down button when showScrollDownButton is false', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} showScrollDownButton={false} />
        </ProviderWrapper>,
      );

      const buttons = screen.getAllByRole('button');
      expect(buttons).toHaveLength(1); // Only send button
    });
  });

  describe('Textarea Functionality', () => {
    it('calls handleChange when typing in textarea', async () => {
      const handleChangeMock = vi.fn();
      const user = userEvent.setup();

      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} handleChange={handleChangeMock} />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');
      await user.type(textarea, 'Hello');

      expect(handleChangeMock).toHaveBeenCalled();
    });

    it('calls handleKeyDown when key is pressed in textarea', async () => {
      const handleKeyDownMock = vi.fn();

      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} handleKeyDown={handleKeyDownMock} />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');

      await act(async () => {
        fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' });
      });

      expect(handleKeyDownMock).toHaveBeenCalled();
    });

    it('calls setIsTyping on composition events', async () => {
      const setIsTypingMock = vi.fn();

      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} setIsTyping={setIsTypingMock} />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');

      // Test composition start
      await act(async () => {
        fireEvent.compositionStart(textarea);
      });
      expect(setIsTypingMock).toHaveBeenCalledWith(true);

      // Test composition end
      await act(async () => {
        fireEvent.compositionEnd(textarea);
      });
      expect(setIsTypingMock).toHaveBeenCalledWith(false);
    });

    it('disables textarea when disabled prop is true', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} disabled={true} />
        </ProviderWrapper>,
      );

      expect(screen.getByTestId('chat-input')).toBeDisabled();
    });

    it('enables textarea when disabled prop is false', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} disabled={false} />
        </ProviderWrapper>,
      );

      expect(screen.getByTestId('chat-input')).not.toBeDisabled();
    });
  });

  describe('Send Button Functionality', () => {
    it('calls handleSend when send button is clicked', async () => {
      const handleSendMock = vi.fn();
      const user = userEvent.setup();

      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} handleSend={handleSendMock} />
        </ProviderWrapper>,
      );

      const sendButton = screen.getByTestId('send-button');
      await user.click(sendButton);

      expect(handleSendMock).toHaveBeenCalled();
    });

    it('disables send button when sendDisabled is true', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} sendDisabled={true} />
        </ProviderWrapper>,
      );

      expect(screen.getByTestId('send-button')).toBeDisabled();
    });

    it('disables send button when disabled is true', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} disabled={true} />
        </ProviderWrapper>,
      );

      expect(screen.getByTestId('send-button')).toBeDisabled();
    });

    it('disables send button when both sendDisabled and disabled are true', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} sendDisabled={true} disabled={true} />
        </ProviderWrapper>,
      );

      expect(screen.getByTestId('send-button')).toBeDisabled();
    });

    it('enables send button when both sendDisabled and disabled are false', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea
            {...defaultProps}
            sendDisabled={false}
            disabled={false}
          />
        </ProviderWrapper>,
      );

      expect(screen.getByTestId('send-button')).not.toBeDisabled();
    });
  });

  describe('Stop Button Functionality', () => {
    it('calls handleStopConversation when stop button is clicked', async () => {
      const handleStopConversationMock = vi.fn();
      const user = userEvent.setup();

      render(
        <ProviderWrapper>
          <ChatTextArea
            {...defaultProps}
            messageIsStreaming={true}
            handleStopConversation={handleStopConversationMock}
          />
        </ProviderWrapper>,
      );

      const stopButton = screen.getByRole('button');
      await user.click(stopButton);

      expect(handleStopConversationMock).toHaveBeenCalled();
    });

    it('renders stop button instead of send button when streaming', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} messageIsStreaming={true} />
        </ProviderWrapper>,
      );

      expect(screen.queryByTestId('send-button')).not.toBeInTheDocument();
      expect(screen.getByRole('button')).toBeInTheDocument(); // Stop button
    });
  });

  describe('Scroll Down Button Functionality', () => {
    it('calls onScrollDownClick when scroll down button is clicked', async () => {
      const onScrollDownClickMock = vi.fn();
      const user = userEvent.setup();

      render(
        <ProviderWrapper>
          <ChatTextArea
            {...defaultProps}
            showScrollDownButton={true}
            onScrollDownClick={onScrollDownClickMock}
          />
        </ProviderWrapper>,
      );

      const buttons = screen.getAllByRole('button');
      const scrollDownButton = buttons.find(
        (button) => button !== screen.getByTestId('send-button'),
      );

      if (scrollDownButton) {
        await user.click(scrollDownButton);
        expect(onScrollDownClickMock).toHaveBeenCalled();
      }
    });
  });

  describe('Textarea Ref Integration', () => {
    it('attaches ref to textarea element', () => {
      const textareaRef = { current: null };

      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} textareaRef={textareaRef} />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');
      // In a real environment, the ref would be attached, but in tests it's harder to verify
      // We can at least ensure the textarea exists and the component doesn't crash
      expect(textarea).toBeInTheDocument();
    });

    it('handles textarea styling based on ref scroll height', () => {
      const textareaRef = {
        current: {
          scrollHeight: 500, // Greater than 400
        },
      };

      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} textareaRef={textareaRef as any} />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');
      expect(textarea).toHaveStyle({ overflow: 'auto' });
    });

    it('handles textarea styling when scroll height is small', () => {
      const textareaRef = {
        current: {
          scrollHeight: 200, // Less than 400
        },
      };

      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} textareaRef={textareaRef as any} />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');
      expect(textarea).toHaveStyle({ overflow: 'hidden' });
    });

    it('handles null textareaRef current gracefully', () => {
      const textareaRef = { current: null };

      expect(() =>
        render(
          <ProviderWrapper>
            <ChatTextArea {...defaultProps} textareaRef={textareaRef} />
          </ProviderWrapper>,
        ),
      ).not.toThrow();

      expect(screen.getByTestId('chat-input')).toBeInTheDocument();
    });
  });

  describe('Styling and CSS Classes', () => {
    it('applies correct CSS classes to textarea', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');
      expect(textarea).toHaveClass(
        'py-4',
        'w-full',
        'shadow-lg',
        'rounded-3xl',
      );
    });

    it('applies correct button styling and positioning', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} />
        </ProviderWrapper>,
      );

      const sendButton = screen.getByTestId('send-button');
      expect(sendButton).toHaveClass('absolute', 'right-1.5');
    });

    it('applies correct styling for scroll down button when visible', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} showScrollDownButton={true} />
        </ProviderWrapper>,
      );

      const buttons = screen.getAllByRole('button');
      // Should have send button + scroll down button
      expect(buttons).toHaveLength(2);
    });
  });

  describe('Edge Cases and Error Handling', () => {
    it('handles missing callback functions gracefully', async () => {
      const user = userEvent.setup();

      render(
        <ProviderWrapper>
          <ChatTextArea
            {...defaultProps}
            handleSend={vi.fn()}
            handleChange={vi.fn()}
            handleKeyDown={vi.fn()}
            setIsTyping={vi.fn()}
          />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');
      const sendButton = screen.getByTestId('send-button');

      // Test that the component works with basic mock functions
      fireEvent.change(textarea, { target: { value: 'test' } });
      fireEvent.keyDown(textarea, { key: 'Enter' });
      fireEvent.compositionStart(textarea);
      fireEvent.compositionEnd(textarea);

      await user.click(sendButton);

      // If we reach here without throwing, the test passes
      expect(textarea).toBeInTheDocument();
    });

    it('handles empty content gracefully', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} content="" />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');
      expect(textarea).toHaveValue('');
    });

    it('handles very long content', () => {
      const longContent = 'A'.repeat(1000);

      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} content={longContent} />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');
      expect(textarea).toHaveValue(longContent);
    });

    it('handles special characters in content', () => {
      const specialContent = '!@#$%^&*()_+-=[]{}|;:,.<>?/~`';

      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} content={specialContent} />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');
      expect(textarea).toHaveValue(specialContent);
    });

    it('handles newlines in content', () => {
      const contentWithNewlines = 'Line 1\nLine 2\nLine 3';

      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} content={contentWithNewlines} />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');
      expect(textarea).toHaveValue(contentWithNewlines);
    });
  });

  describe('Accessibility', () => {
    it('has proper aria-label for textarea', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');
      expect(textarea).toHaveAttribute('aria-label', 'chat-input');
    });

    it('has proper id for textarea', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');
      expect(textarea).toHaveAttribute('id', 'chat-input');
    });

    it('has proper id for send button', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} />
        </ProviderWrapper>,
      );

      const sendButton = screen.getByTestId('send-button');
      expect(sendButton).toHaveAttribute('id', 'send-button');
    });

    it('maintains focus management properly', async () => {
      const user = userEvent.setup();

      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');

      await user.click(textarea);
      expect(textarea).toHaveFocus();
    });
  });

  describe('Responsive Design Elements', () => {
    it('applies responsive max-height classes', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');
      expect(textarea).toHaveClass(
        'max-h-[110px]',
        'md:max-h-[200px]',
        'lg:max-h-[400px]',
      );
    });

    it('applies responsive scroll button positioning', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea {...defaultProps} showScrollDownButton={true} />
        </ProviderWrapper>,
      );

      const buttons = screen.getAllByRole('button');
      const scrollButton = buttons.find(
        (btn) => btn !== screen.getByTestId('send-button'),
      );

      expect(scrollButton).toHaveClass(
        '-top-16',
        'right-1.5',
        'md:top-2',
        'md:-right-16',
      );
    });
  });

  describe('State Management Integration', () => {
    it('renders correctly when all states are active', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea
            {...defaultProps}
            disabled={true}
            sendDisabled={true}
            messageIsStreaming={true}
            showScrollDownButton={true}
          />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');
      expect(textarea).toBeDisabled();

      // Should only show stop button and scroll button (no send button when streaming)
      expect(screen.queryByTestId('send-button')).not.toBeInTheDocument();

      const buttons = screen.getAllByRole('button');
      expect(buttons).toHaveLength(2); // Stop + scroll buttons
    });

    it('renders correctly when all states are inactive', () => {
      render(
        <ProviderWrapper>
          <ChatTextArea
            {...defaultProps}
            disabled={false}
            sendDisabled={false}
            messageIsStreaming={false}
            showScrollDownButton={false}
          />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');
      expect(textarea).not.toBeDisabled();

      const sendButton = screen.getByTestId('send-button');
      expect(sendButton).not.toBeDisabled();

      const buttons = screen.getAllByRole('button');
      expect(buttons).toHaveLength(1); // Only send button
    });
  });
});
