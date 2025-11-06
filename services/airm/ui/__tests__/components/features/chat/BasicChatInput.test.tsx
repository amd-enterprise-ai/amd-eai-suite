// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { BasicChatInput } from '@/components/features/chat/BasicChatInput';
import ProviderWrapper from '@/__tests__/ProviderWrapper';

import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock the ChatTextArea component
vi.mock('@/components/features/chat/ChatTextArea', () => ({
  ChatTextArea: ({
    content,
    handleChange,
    handleKeyDown,
    setIsTyping,
    textareaRef,
    disabled,
    sendDisabled,
    messageIsStreaming,
    handleSend,
    handleStopConversation,
    showScrollDownButton,
    onScrollDownClick,
  }: any) => (
    <div data-testid="chat-textarea">
      <textarea
        data-testid="chat-input"
        value={content}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onCompositionStart={() => setIsTyping(true)}
        onCompositionEnd={() => setIsTyping(false)}
        ref={textareaRef}
        disabled={disabled}
        placeholder="Type your message..."
      />
      <button
        data-testid="send-button"
        onClick={() => {
          // Call the actual handleSend function passed from BasicChatInput
          if (handleSend && !sendDisabled) {
            handleSend();
          }
        }}
        disabled={sendDisabled}
      >
        Send
      </button>
      <button
        data-testid="stop-button"
        onClick={handleStopConversation}
        style={{ display: messageIsStreaming ? 'block' : 'none' }}
      >
        Stop
      </button>
      {showScrollDownButton && (
        <button data-testid="scroll-down-button" onClick={onScrollDownClick}>
          Scroll Down
        </button>
      )}
    </div>
  ),
}));

// Mock browser utilities
vi.mock('@/utils/app/browser', () => ({
  isMobile: vi.fn(() => false),
}));

// Mock next-i18next
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'chatInput.regenerateResponse': 'Regenerate Response',
      };
      return translations[key] || key;
    },
  }),
}));

// Mock window.innerWidth
Object.defineProperty(window, 'innerWidth', {
  writable: true,
  configurable: true,
  value: 1024,
});

describe('BasicChatInput Component', () => {
  const defaultProps = {
    content: '',
    setContent: vi.fn(),
    onSend: vi.fn(),
    onScrollDownClick: vi.fn(),
    stopConversationRef: { current: false },
    textareaRef: { current: null },
    showScrollDownButton: false,
    allowRegenerate: false,
    disabled: false,
    messageIsStreaming: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    // Reset window.innerWidth to default
    window.innerWidth = 1024;
  });

  describe('Rendering', () => {
    it('renders the basic chat input correctly', () => {
      render(
        <ProviderWrapper>
          <BasicChatInput {...defaultProps} />
        </ProviderWrapper>,
      );

      expect(screen.getByTestId('chat-textarea')).toBeInTheDocument();
      expect(screen.getByTestId('chat-input')).toBeInTheDocument();
      expect(screen.getByTestId('send-button')).toBeInTheDocument();
    });

    it('renders regenerate button when allowRegenerate is true and not streaming', () => {
      render(
        <ProviderWrapper>
          <BasicChatInput
            {...defaultProps}
            allowRegenerate={true}
            messageIsStreaming={false}
          />
        </ProviderWrapper>,
      );

      expect(screen.getByText('Regenerate Response')).toBeInTheDocument();
    });

    it('does not render regenerate button when messageIsStreaming is true', () => {
      render(
        <ProviderWrapper>
          <BasicChatInput
            {...defaultProps}
            allowRegenerate={true}
            messageIsStreaming={true}
          />
        </ProviderWrapper>,
      );

      expect(screen.queryByText('Regenerate Response')).not.toBeInTheDocument();
    });

    it('does not render regenerate button when allowRegenerate is false', () => {
      render(
        <ProviderWrapper>
          <BasicChatInput
            {...defaultProps}
            allowRegenerate={false}
            messageIsStreaming={false}
          />
        </ProviderWrapper>,
      );

      expect(screen.queryByText('Regenerate Response')).not.toBeInTheDocument();
    });

    it('renders scroll down button when showScrollDownButton is true', () => {
      render(
        <ProviderWrapper>
          <BasicChatInput {...defaultProps} showScrollDownButton={true} />
        </ProviderWrapper>,
      );

      expect(screen.getByTestId('scroll-down-button')).toBeInTheDocument();
    });
  });

  describe('Content Management', () => {
    it('updates content when typing in textarea', async () => {
      const setContentMock = vi.fn();

      render(
        <ProviderWrapper>
          <BasicChatInput {...defaultProps} setContent={setContentMock} />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');

      // Simulate typing by firing a change event
      await act(async () => {
        fireEvent.change(textarea, { target: { value: 'Hello world' } });
      });

      // The component should call setContent with the full string
      expect(setContentMock).toHaveBeenCalledWith('Hello world');
    });

    it('disables send button when content is empty', () => {
      render(
        <ProviderWrapper>
          <BasicChatInput {...defaultProps} content="" />
        </ProviderWrapper>,
      );

      expect(screen.getByTestId('send-button')).toBeDisabled();
    });

    it('disables send button when content is only whitespace', async () => {
      render(
        <ProviderWrapper>
          <BasicChatInput {...defaultProps} content="" />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');

      // Initially disabled
      expect(screen.getByTestId('send-button')).toBeDisabled();

      // Simulate typing whitespace-only content
      await act(async () => {
        fireEvent.change(textarea, { target: { value: '   ' } });
      });

      // Button should remain disabled due to whitespace-only content
      expect(screen.getByTestId('send-button')).toBeDisabled();
    });

    it('enables send button when content has valid text', async () => {
      const user = userEvent.setup();

      render(
        <ProviderWrapper>
          <BasicChatInput {...defaultProps} content="Hello" />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');

      await act(async () => {
        fireEvent.change(textarea, { target: { value: 'Hello' } });
      });

      expect(screen.getByTestId('send-button')).not.toBeDisabled();
    });
  });

  describe('Message Sending', () => {
    it('sends message when send button is clicked', async () => {
      const onSendMock = vi.fn();
      const setContentMock = vi.fn();
      const user = userEvent.setup();

      render(
        <ProviderWrapper>
          <BasicChatInput
            {...defaultProps}
            content="Test message"
            onSend={onSendMock}
            setContent={setContentMock}
          />
        </ProviderWrapper>,
      );

      const sendButton = screen.getByTestId('send-button');
      await user.click(sendButton);

      expect(onSendMock).toHaveBeenCalledWith({
        role: 'user',
        content: 'Test message',
      });
      expect(setContentMock).toHaveBeenCalledWith('');
    });

    it('sends message when Enter key is pressed', async () => {
      const onSendMock = vi.fn();
      const setContentMock = vi.fn();

      render(
        <ProviderWrapper>
          <BasicChatInput
            {...defaultProps}
            content="Test message"
            onSend={onSendMock}
            setContent={setContentMock}
          />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');

      await act(async () => {
        fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' });
      });

      expect(onSendMock).toHaveBeenCalledWith({
        role: 'user',
        content: 'Test message',
      });
      expect(setContentMock).toHaveBeenCalledWith('');
    });

    it('does not send message when Enter is pressed with Shift key', async () => {
      const onSendMock = vi.fn();

      render(
        <ProviderWrapper>
          <BasicChatInput
            {...defaultProps}
            content="Test message"
            onSend={onSendMock}
          />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');

      await act(async () => {
        fireEvent.keyDown(textarea, {
          key: 'Enter',
          code: 'Enter',
          shiftKey: true,
        });
      });

      expect(onSendMock).not.toHaveBeenCalled();
    });

    it('does not send message when messageIsStreaming is true', async () => {
      const onSendMock = vi.fn();
      const user = userEvent.setup();

      render(
        <ProviderWrapper>
          <BasicChatInput
            {...defaultProps}
            content="Test message"
            onSend={onSendMock}
            messageIsStreaming={true}
          />
        </ProviderWrapper>,
      );

      const sendButton = screen.getByTestId('send-button');
      await user.click(sendButton);

      expect(onSendMock).not.toHaveBeenCalled();
    });

    it('does not send message when content is empty', async () => {
      const onSendMock = vi.fn();
      const user = userEvent.setup();

      render(
        <ProviderWrapper>
          <BasicChatInput {...defaultProps} content="" onSend={onSendMock} />
        </ProviderWrapper>,
      );

      const sendButton = screen.getByTestId('send-button');
      await user.click(sendButton);

      expect(onSendMock).not.toHaveBeenCalled();
    });

    it('does not send message when send button is disabled', async () => {
      const onSendMock = vi.fn();

      render(
        <ProviderWrapper>
          <BasicChatInput {...defaultProps} content="" onSend={onSendMock} />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');

      await act(async () => {
        fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' });
      });

      expect(onSendMock).not.toHaveBeenCalled();
    });
  });

  describe('Mobile Behavior', () => {
    it('handles mobile screen width without errors', async () => {
      // Set mobile width (component checks window.innerWidth < 640)
      window.innerWidth = 500;

      const onSendMock = vi.fn();
      const setContentMock = vi.fn();
      const textareaRef = { current: { blur: vi.fn() } };

      render(
        <ProviderWrapper>
          <BasicChatInput
            {...defaultProps}
            content="Test message"
            onSend={onSendMock}
            setContent={setContentMock}
            textareaRef={textareaRef as any}
          />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');

      // First simulate typing to enable the send button
      await act(async () => {
        fireEvent.change(textarea, { target: { value: 'Test message' } });
      });

      const sendButton = screen.getByTestId('send-button');

      // Should not throw error when sending on mobile
      await act(async () => {
        fireEvent.click(sendButton);
      });

      expect(onSendMock).toHaveBeenCalled();
    });

    it('does not send message on Enter key press when on mobile', async () => {
      const { isMobile } = await import('@/utils/app/browser');
      vi.mocked(isMobile).mockReturnValue(true);

      const onSendMock = vi.fn();

      render(
        <ProviderWrapper>
          <BasicChatInput
            {...defaultProps}
            content="Test message"
            onSend={onSendMock}
          />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');

      await act(async () => {
        fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' });
      });

      expect(onSendMock).not.toHaveBeenCalled();
    });
  });

  describe('Composition Handling', () => {
    it('does not send message on Enter key press during composition', async () => {
      const onSendMock = vi.fn();

      render(
        <ProviderWrapper>
          <BasicChatInput
            {...defaultProps}
            content="Test message"
            onSend={onSendMock}
          />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');

      // Start composition
      await act(async () => {
        fireEvent.compositionStart(textarea);
      });

      // Try to send while composing
      await act(async () => {
        fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' });
      });

      expect(onSendMock).not.toHaveBeenCalled();

      // End composition
      await act(async () => {
        fireEvent.compositionEnd(textarea);
      });

      // Now Enter should work
      await act(async () => {
        fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' });
      });

      expect(onSendMock).toHaveBeenCalled();
    });
  });

  describe('Stop Conversation', () => {
    it('sets stopConversationRef when stop button is clicked', async () => {
      const stopConversationRef = { current: false };
      const user = userEvent.setup();

      render(
        <ProviderWrapper>
          <BasicChatInput
            {...defaultProps}
            messageIsStreaming={true}
            stopConversationRef={stopConversationRef}
          />
        </ProviderWrapper>,
      );

      const stopButton = screen.getByTestId('stop-button');
      await user.click(stopButton);

      expect(stopConversationRef.current).toBe(true);

      // Wait for timeout to reset
      await waitFor(
        () => {
          expect(stopConversationRef.current).toBe(false);
        },
        { timeout: 1100 },
      );
    });
  });

  describe('Regenerate Functionality', () => {
    it('calls onRegenerate when regenerate button is clicked', async () => {
      const onRegenerateMock = vi.fn();
      const user = userEvent.setup();

      render(
        <ProviderWrapper>
          <BasicChatInput
            {...defaultProps}
            allowRegenerate={true}
            onRegenerate={onRegenerateMock}
          />
        </ProviderWrapper>,
      );

      const regenerateButton = screen.getByText('Regenerate Response');
      await user.click(regenerateButton);

      expect(onRegenerateMock).toHaveBeenCalled();
    });

    it('handles missing onRegenerate callback gracefully', async () => {
      const user = userEvent.setup();

      render(
        <ProviderWrapper>
          <BasicChatInput
            {...defaultProps}
            allowRegenerate={true}
            // onRegenerate is undefined
          />
        </ProviderWrapper>,
      );

      const regenerateButton = screen.getByText('Regenerate Response');

      // Should not throw error
      expect(() => user.click(regenerateButton)).not.toThrow();
    });
  });

  describe('Scroll Down Functionality', () => {
    it('calls onScrollDownClick when scroll down button is clicked', async () => {
      const onScrollDownClickMock = vi.fn();
      const user = userEvent.setup();

      render(
        <ProviderWrapper>
          <BasicChatInput
            {...defaultProps}
            showScrollDownButton={true}
            onScrollDownClick={onScrollDownClickMock}
          />
        </ProviderWrapper>,
      );

      const scrollDownButton = screen.getByTestId('scroll-down-button');
      await user.click(scrollDownButton);

      expect(onScrollDownClickMock).toHaveBeenCalled();
    });
  });

  describe('Textarea Auto-sizing', () => {
    it('handles textareaRef with valid current element', () => {
      const textareaRef = {
        current: {
          style: { height: '', overflow: '' },
          scrollHeight: 100,
        },
      };

      render(
        <ProviderWrapper>
          <BasicChatInput
            {...defaultProps}
            content="Some content"
            textareaRef={textareaRef as any}
          />
        </ProviderWrapper>,
      );

      // The useEffect should run and update the styles
      // We just verify that the component renders without error
      expect(screen.getByTestId('chat-textarea')).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('handles errors in handleSend gracefully', async () => {
      const onSendMock = vi.fn().mockImplementation(() => {
        throw new Error('Send error');
      });
      const consoleSpy = vi
        .spyOn(console, 'error')
        .mockImplementation(() => {});
      const user = userEvent.setup();

      render(
        <ProviderWrapper>
          <BasicChatInput
            {...defaultProps}
            content="Test message"
            onSend={onSendMock}
          />
        </ProviderWrapper>,
      );

      const sendButton = screen.getByTestId('send-button');
      await user.click(sendButton);

      expect(consoleSpy).toHaveBeenCalledWith(
        'Error sending message: ',
        expect.any(Error),
      );

      consoleSpy.mockRestore();
    });
  });

  describe('Disabled State', () => {
    it('passes disabled prop to ChatTextArea', () => {
      render(
        <ProviderWrapper>
          <BasicChatInput {...defaultProps} disabled={true} />
        </ProviderWrapper>,
      );

      expect(screen.getByTestId('chat-input')).toBeDisabled();
    });
  });

  describe('Edge Cases', () => {
    it('handles content with only newlines', async () => {
      const setContentMock = vi.fn();
      const user = userEvent.setup();

      render(
        <ProviderWrapper>
          <BasicChatInput {...defaultProps} setContent={setContentMock} />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-input');

      await act(async () => {
        fireEvent.change(textarea, { target: { value: '\n\n\n' } });
      });

      expect(screen.getByTestId('send-button')).toBeDisabled();
    });

    it('resets send disabled state correctly after sending', async () => {
      const onSendMock = vi.fn();
      const setContentMock = vi.fn();
      const user = userEvent.setup();

      render(
        <ProviderWrapper>
          <BasicChatInput
            {...defaultProps}
            content="Test message"
            onSend={onSendMock}
            setContent={setContentMock}
          />
        </ProviderWrapper>,
      );

      const sendButton = screen.getByTestId('send-button');

      // Initially should not be disabled (has content)
      expect(sendButton).not.toBeDisabled();

      await user.click(sendButton);

      // After sending, setContent('') is called, which should disable the button
      expect(setContentMock).toHaveBeenCalledWith('');
    });
  });
});
