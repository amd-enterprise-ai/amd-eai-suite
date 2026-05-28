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

const toastErrorMock = vi.fn();
const toastWarningMock = vi.fn();

vi.mock('@amdenterpriseai/hooks', () => ({
  useSystemToast: () => ({
    toast: {
      error: toastErrorMock,
      warning: toastWarningMock,
      success: vi.fn(),
    },
  }),
}));

// Mock the ChatTextArea component
vi.mock('@/components/features/chat/ChatTextArea', () => ({
  ChatTextArea: ({
    content,
    enableImageInput,
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
    onAttachImage,
    hasAttachedImages,
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
      {enableImageInput && onAttachImage && (
        <button
          data-testid="attach-image-button"
          onClick={onAttachImage}
          data-has-images={hasAttachedImages ? 'true' : 'false'}
        >
          Attach
        </button>
      )}
    </div>
  ),
}));

// Mock next/image
vi.mock('next/image', () => ({
  default: ({ src, alt, ...props }: any) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt={alt} {...props} />
  ),
}));

// Mock image-utils
vi.mock('@/lib/app/image-utils', () => ({
  fileToBase64DataUrl: vi.fn(),
  isSupportedImageFormat: vi.fn(),
  isImageFileTooLarge: vi.fn(),
  formatFileSize: vi.fn(),
  MAX_IMAGE_FILE_SIZE: 20 * 1024 * 1024,
  MAX_TOTAL_ATTACHMENT_SIZE: 70 * 1024 * 1024,
}));

// Mock browser utilities
vi.mock('@/lib/app/browser', () => ({
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
          <BasicChatInput enableImageInput={false} {...defaultProps} />
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
            enableImageInput={false}
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
            enableImageInput={false}
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
            enableImageInput={false}
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
          <BasicChatInput
            enableImageInput={false}
            {...defaultProps}
            showScrollDownButton={true}
          />
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
          <BasicChatInput
            enableImageInput={false}
            {...defaultProps}
            setContent={setContentMock}
          />
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
          <BasicChatInput
            enableImageInput={false}
            {...defaultProps}
            content=""
          />
        </ProviderWrapper>,
      );

      expect(screen.getByTestId('send-button')).toBeDisabled();
    });

    it('disables send button when content is only whitespace', async () => {
      render(
        <ProviderWrapper>
          <BasicChatInput
            enableImageInput={false}
            {...defaultProps}
            content=""
          />
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
          <BasicChatInput
            enableImageInput={false}
            {...defaultProps}
            content="Hello"
          />
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
            enableImageInput={false}
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
            enableImageInput={false}
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
            enableImageInput={false}
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
            enableImageInput={false}
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
          <BasicChatInput
            enableImageInput={false}
            {...defaultProps}
            content=""
            onSend={onSendMock}
          />
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
          <BasicChatInput
            enableImageInput={false}
            {...defaultProps}
            content=""
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
            enableImageInput={false}
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
      const { isMobile } = await import('@/lib/app/browser');
      vi.mocked(isMobile).mockReturnValue(true);

      const onSendMock = vi.fn();

      render(
        <ProviderWrapper>
          <BasicChatInput
            enableImageInput={false}
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
            enableImageInput={false}
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
            enableImageInput={false}
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
            enableImageInput={false}
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
            enableImageInput={false}
            {...defaultProps}
            allowRegenerate={true} // onRegenerate is undefined
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
            enableImageInput={false}
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
            enableImageInput={false}
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
      const user = userEvent.setup();

      render(
        <ProviderWrapper>
          <BasicChatInput
            enableImageInput={false}
            {...defaultProps}
            content="Test message"
            onSend={onSendMock}
          />
        </ProviderWrapper>,
      );

      const sendButton = screen.getByTestId('send-button');
      await user.click(sendButton);

      expect(toastErrorMock).toHaveBeenCalled();
    });
  });

  describe('Embedded layout', () => {
    it('uses full-width flush layout when embedded', () => {
      render(
        <ProviderWrapper>
          <BasicChatInput enableImageInput={false} {...defaultProps} embedded />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-textarea');
      // chat-textarea → flex-col div → inner div → outer div (the one with layout class)
      const outerWrapper = textarea.parentElement?.parentElement?.parentElement;
      expect(outerWrapper).toHaveClass(
        'flex',
        'w-full',
        'justify-start',
        'py-0',
      );
    });

    it('uses centered constrained layout when not embedded', () => {
      render(
        <ProviderWrapper>
          <BasicChatInput enableImageInput={false} {...defaultProps} />
        </ProviderWrapper>,
      );

      const textarea = screen.getByTestId('chat-textarea');
      // chat-textarea → flex-col div → inner div → outer div (the one with layout class)
      const outerWrapper = textarea.parentElement?.parentElement?.parentElement;
      expect(outerWrapper).toHaveClass('flex', 'justify-center', 'py-6');
    });
  });

  describe('Disabled State', () => {
    it('passes disabled prop to ChatTextArea', () => {
      render(
        <ProviderWrapper>
          <BasicChatInput
            enableImageInput={false}
            {...defaultProps}
            disabled={true}
          />
        </ProviderWrapper>,
      );

      expect(screen.getByTestId('chat-input')).toBeDisabled();
    });
  });

  describe('Image Attachment', () => {
    let fileToBase64DataUrl: ReturnType<typeof vi.fn>;
    let isSupportedImageFormat: ReturnType<typeof vi.fn>;
    let isImageFileTooLarge: ReturnType<typeof vi.fn>;

    beforeEach(async () => {
      const imageUtils = await import('@/lib/app/image-utils');
      fileToBase64DataUrl = vi.mocked(imageUtils.fileToBase64DataUrl);
      isSupportedImageFormat = vi.mocked(imageUtils.isSupportedImageFormat);
      isImageFileTooLarge = vi.mocked(imageUtils.isImageFileTooLarge);
      isImageFileTooLarge.mockReturnValue(false);
    });

    const makeImageFile = (name = 'photo.png', type = 'image/png') =>
      new File(['img'], name, { type });

    it('shows the attach-image button via ChatTextArea', () => {
      render(
        <ProviderWrapper>
          <BasicChatInput enableImageInput={true} {...defaultProps} />
        </ProviderWrapper>,
      );

      // The hidden file input triggers the attach-image button in ChatTextArea
      expect(screen.getByTestId('attach-image-button')).toBeInTheDocument();
    });

    it('clicking the attach-image button triggers the hidden file input', async () => {
      const user = userEvent.setup();

      render(
        <ProviderWrapper>
          <BasicChatInput enableImageInput={true} {...defaultProps} />
        </ProviderWrapper>,
      );

      const fileInput = document.querySelector(
        'input[type="file"]',
      ) as HTMLInputElement;
      const clickSpy = vi.spyOn(fileInput, 'click');

      await user.click(screen.getByTestId('attach-image-button'));

      expect(clickSpy).toHaveBeenCalled();
    });

    it('attaches a valid image and shows its preview', async () => {
      const fakeDataUrl = 'data:image/png;base64,abc';
      isSupportedImageFormat.mockReturnValue(true);
      fileToBase64DataUrl.mockResolvedValue(fakeDataUrl);

      const { container } = render(
        <ProviderWrapper>
          <BasicChatInput enableImageInput={true} {...defaultProps} />
        </ProviderWrapper>,
      );

      const fileInput = container.querySelector(
        'input[type="file"]',
      ) as HTMLInputElement;

      await act(async () => {
        fireEvent.change(fileInput, {
          target: { files: [makeImageFile()] },
        });
      });

      await waitFor(() => {
        expect(screen.getByAltText('photo.png')).toBeInTheDocument();
      });
    });

    it('enables send button after a valid image is attached', async () => {
      isSupportedImageFormat.mockReturnValue(true);
      fileToBase64DataUrl.mockResolvedValue('data:image/png;base64,abc');

      const { container } = render(
        <ProviderWrapper>
          <BasicChatInput
            enableImageInput={true}
            {...defaultProps}
            content=""
          />
        </ProviderWrapper>,
      );

      // Initially disabled (no content, no images)
      expect(screen.getByTestId('send-button')).toBeDisabled();

      const fileInput = container.querySelector(
        'input[type="file"]',
      ) as HTMLInputElement;

      await act(async () => {
        fireEvent.change(fileInput, {
          target: { files: [makeImageFile()] },
        });
      });

      await waitFor(() => {
        expect(screen.getByTestId('send-button')).not.toBeDisabled();
      });
    });

    it('marks hasAttachedImages on the attach button after an image is attached', async () => {
      isSupportedImageFormat.mockReturnValue(true);
      fileToBase64DataUrl.mockResolvedValue('data:image/png;base64,abc');

      const { container } = render(
        <ProviderWrapper>
          <BasicChatInput enableImageInput={true} {...defaultProps} />
        </ProviderWrapper>,
      );

      const fileInput = container.querySelector(
        'input[type="file"]',
      ) as HTMLInputElement;

      await act(async () => {
        fireEvent.change(fileInput, {
          target: { files: [makeImageFile()] },
        });
      });

      await waitFor(() => {
        expect(screen.getByTestId('attach-image-button')).toHaveAttribute(
          'data-has-images',
          'true',
        );
      });
    });

    it('removes an image when the remove button is clicked', async () => {
      isSupportedImageFormat.mockReturnValue(true);
      fileToBase64DataUrl.mockResolvedValue('data:image/png;base64,abc');

      const { container } = render(
        <ProviderWrapper>
          <BasicChatInput enableImageInput={true} {...defaultProps} />
        </ProviderWrapper>,
      );

      const fileInput = container.querySelector(
        'input[type="file"]',
      ) as HTMLInputElement;

      await act(async () => {
        fireEvent.change(fileInput, {
          target: { files: [makeImageFile()] },
        });
      });

      await waitFor(() => {
        expect(screen.getByAltText('photo.png')).toBeInTheDocument();
      });

      const removeButton = screen.getByTitle('chatInput.removeImage');
      await act(async () => {
        fireEvent.click(removeButton);
      });

      expect(screen.queryByAltText('photo.png')).not.toBeInTheDocument();
    });

    it('disables send button after removing the only attached image (no text)', async () => {
      isSupportedImageFormat.mockReturnValue(true);
      fileToBase64DataUrl.mockResolvedValue('data:image/png;base64,abc');

      const { container } = render(
        <ProviderWrapper>
          <BasicChatInput
            enableImageInput={true}
            {...defaultProps}
            content=""
          />
        </ProviderWrapper>,
      );

      const fileInput = container.querySelector(
        'input[type="file"]',
      ) as HTMLInputElement;

      await act(async () => {
        fireEvent.change(fileInput, { target: { files: [makeImageFile()] } });
      });

      await waitFor(() => {
        expect(screen.getByTestId('send-button')).not.toBeDisabled();
      });

      await act(async () => {
        fireEvent.click(screen.getByTitle('chatInput.removeImage'));
      });

      expect(screen.getByTestId('send-button')).toBeDisabled();
    });

    it('sends a message with image-only content (adds default space text)', async () => {
      isSupportedImageFormat.mockReturnValue(true);
      const fakeDataUrl = 'data:image/png;base64,abc';
      fileToBase64DataUrl.mockResolvedValue(fakeDataUrl);

      const onSendMock = vi.fn();

      const { container } = render(
        <ProviderWrapper>
          <BasicChatInput
            enableImageInput={true}
            {...defaultProps}
            content=""
            onSend={onSendMock}
          />
        </ProviderWrapper>,
      );

      const fileInput = container.querySelector(
        'input[type="file"]',
      ) as HTMLInputElement;

      await act(async () => {
        fireEvent.change(fileInput, { target: { files: [makeImageFile()] } });
      });

      await waitFor(() => {
        expect(screen.getByTestId('send-button')).not.toBeDisabled();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId('send-button'));
      });

      expect(onSendMock).toHaveBeenCalledWith({
        role: 'user',
        content: [
          { type: 'text', text: ' ' },
          { type: 'image_url', image_url: { url: fakeDataUrl } },
        ],
      });
    });

    it('sends a message with text + image content', async () => {
      isSupportedImageFormat.mockReturnValue(true);
      const fakeDataUrl = 'data:image/png;base64,abc';
      fileToBase64DataUrl.mockResolvedValue(fakeDataUrl);

      const onSendMock = vi.fn();

      const { container } = render(
        <ProviderWrapper>
          <BasicChatInput
            enableImageInput={true}
            {...defaultProps}
            content="describe this"
            onSend={onSendMock}
          />
        </ProviderWrapper>,
      );

      const fileInput = container.querySelector(
        'input[type="file"]',
      ) as HTMLInputElement;

      await act(async () => {
        fireEvent.change(fileInput, { target: { files: [makeImageFile()] } });
      });

      await waitFor(() => {
        expect(screen.getByAltText('photo.png')).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId('send-button'));
      });

      expect(onSendMock).toHaveBeenCalledWith({
        role: 'user',
        content: [
          { type: 'text', text: 'describe this' },
          { type: 'image_url', image_url: { url: fakeDataUrl } },
        ],
      });
    });

    it('clears attached images after sending', async () => {
      isSupportedImageFormat.mockReturnValue(true);
      fileToBase64DataUrl.mockResolvedValue('data:image/png;base64,abc');

      const { container } = render(
        <ProviderWrapper>
          <BasicChatInput
            enableImageInput={true}
            {...defaultProps}
            content="hi"
            onSend={vi.fn()}
          />
        </ProviderWrapper>,
      );

      const fileInput = container.querySelector(
        'input[type="file"]',
      ) as HTMLInputElement;

      await act(async () => {
        fireEvent.change(fileInput, { target: { files: [makeImageFile()] } });
      });

      await waitFor(() => {
        expect(screen.getByAltText('photo.png')).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId('send-button'));
      });

      expect(screen.queryByAltText('photo.png')).not.toBeInTheDocument();
    });

    it('shows an error toast and skips preview for unsupported format', async () => {
      isSupportedImageFormat.mockReturnValue(false);

      const { container } = render(
        <ProviderWrapper>
          <BasicChatInput enableImageInput={true} {...defaultProps} />
        </ProviderWrapper>,
      );

      const fileInput = container.querySelector(
        'input[type="file"]',
      ) as HTMLInputElement;

      await act(async () => {
        fireEvent.change(fileInput, {
          target: { files: [makeImageFile('bad.pdf', 'application/pdf')] },
        });
      });

      expect(toastErrorMock).toHaveBeenCalledWith(
        expect.stringContaining('errors.invalidImageFile'),
      );
      expect(screen.queryByRole('img')).not.toBeInTheDocument();
    });

    it('shows an error toast and skips preview for oversized image', async () => {
      isSupportedImageFormat.mockReturnValue(true);
      isImageFileTooLarge.mockReturnValue(true);

      const { container } = render(
        <ProviderWrapper>
          <BasicChatInput enableImageInput={true} {...defaultProps} />
        </ProviderWrapper>,
      );

      const fileInput = container.querySelector(
        'input[type="file"]',
      ) as HTMLInputElement;

      await act(async () => {
        fireEvent.change(fileInput, {
          target: { files: [makeImageFile('huge.png')] },
        });
      });

      expect(toastErrorMock).toHaveBeenCalledWith(
        expect.stringContaining('errors.imageTooLarge'),
      );
      expect(screen.queryByRole('img')).not.toBeInTheDocument();
    });

    it('attaches multiple images and shows all previews', async () => {
      isSupportedImageFormat.mockReturnValue(true);
      fileToBase64DataUrl
        .mockResolvedValueOnce('data:image/png;base64,aaa')
        .mockResolvedValueOnce('data:image/png;base64,bbb');

      const { container } = render(
        <ProviderWrapper>
          <BasicChatInput enableImageInput={true} {...defaultProps} />
        </ProviderWrapper>,
      );

      const fileInput = container.querySelector(
        'input[type="file"]',
      ) as HTMLInputElement;

      await act(async () => {
        fireEvent.change(fileInput, {
          target: {
            files: [makeImageFile('a.png'), makeImageFile('b.png')],
          },
        });
      });

      await waitFor(() => {
        expect(screen.getByAltText('a.png')).toBeInTheDocument();
        expect(screen.getByAltText('b.png')).toBeInTheDocument();
      });
    });

    it('shows a total-size error toast and skips the file when adding it would exceed the total budget', async () => {
      const MAX_TOTAL = 70 * 1024 * 1024;
      isSupportedImageFormat.mockReturnValue(true);
      isImageFileTooLarge.mockReturnValue(false);
      // First image: just under the individual limit, accepted
      fileToBase64DataUrl.mockResolvedValueOnce('data:image/png;base64,aaa');

      const { container } = render(
        <ProviderWrapper>
          <BasicChatInput enableImageInput={true} {...defaultProps} />
        </ProviderWrapper>,
      );

      const fileInput = container.querySelector(
        'input[type="file"]',
      ) as HTMLInputElement;

      // Attach a large-but-valid first image (60 MB raw)
      const bigFile = new File([new ArrayBuffer(60 * 1024 * 1024)], 'big.png', {
        type: 'image/png',
      });
      await act(async () => {
        fireEvent.change(fileInput, { target: { files: [bigFile] } });
      });

      await waitFor(() => {
        expect(screen.getByAltText('big.png')).toBeInTheDocument();
      });

      // Now attach a second image that would push the total over 70 MB
      const overflowFile = new File(
        [new ArrayBuffer(11 * 1024 * 1024)],
        'overflow.png',
        { type: 'image/png' },
      );
      await act(async () => {
        fireEvent.change(fileInput, { target: { files: [overflowFile] } });
      });

      expect(toastErrorMock).toHaveBeenCalledWith(
        expect.stringContaining('errors.totalAttachmentTooLarge'),
      );
      expect(screen.queryByAltText('overflow.png')).not.toBeInTheDocument();
    });

    it('allows a file that fits within the remaining total budget', async () => {
      isSupportedImageFormat.mockReturnValue(true);
      isImageFileTooLarge.mockReturnValue(false);
      fileToBase64DataUrl
        .mockResolvedValueOnce('data:image/png;base64,aaa')
        .mockResolvedValueOnce('data:image/png;base64,bbb');

      const { container } = render(
        <ProviderWrapper>
          <BasicChatInput enableImageInput={true} {...defaultProps} />
        </ProviderWrapper>,
      );

      const fileInput = container.querySelector(
        'input[type="file"]',
      ) as HTMLInputElement;

      // First image: 30 MB
      const firstFile = new File(
        [new ArrayBuffer(30 * 1024 * 1024)],
        'first.png',
        { type: 'image/png' },
      );
      await act(async () => {
        fireEvent.change(fileInput, { target: { files: [firstFile] } });
      });

      await waitFor(() => {
        expect(screen.getByAltText('first.png')).toBeInTheDocument();
      });

      // Second image: 20 MB — 30 + 20 = 50 MB, still under 70 MB limit
      const secondFile = new File(
        [new ArrayBuffer(20 * 1024 * 1024)],
        'second.png',
        { type: 'image/png' },
      );
      await act(async () => {
        fireEvent.change(fileInput, { target: { files: [secondFile] } });
      });

      await waitFor(() => {
        expect(screen.getByAltText('second.png')).toBeInTheDocument();
      });

      expect(toastErrorMock).not.toHaveBeenCalled();
    });
  });

  describe('Drag and Drop', () => {
    let fileToBase64DataUrl: ReturnType<typeof vi.fn>;
    let isSupportedImageFormat: ReturnType<typeof vi.fn>;
    let isImageFileTooLarge: ReturnType<typeof vi.fn>;

    beforeEach(async () => {
      const imageUtils = await import('@/lib/app/image-utils');
      fileToBase64DataUrl = vi.mocked(imageUtils.fileToBase64DataUrl);
      isSupportedImageFormat = vi.mocked(imageUtils.isSupportedImageFormat);
      isImageFileTooLarge = vi.mocked(imageUtils.isImageFileTooLarge);
      isImageFileTooLarge.mockReturnValue(false);
    });

    const makeImageFile = (name = 'photo.png', type = 'image/png') =>
      new File(['img'], name, { type });

    const getDragContainer = () => {
      const textarea = screen.getByTestId('chat-textarea');
      // chat-textarea → flex-col div (drag container) → inner div → outer div
      return textarea.parentElement as HTMLElement;
    };

    it('shows drag overlay when dragging over the input area with enableImageInput', async () => {
      render(
        <ProviderWrapper>
          <BasicChatInput enableImageInput={true} {...defaultProps} />
        </ProviderWrapper>,
      );

      const container = getDragContainer();

      await act(async () => {
        fireEvent.dragOver(container, {
          dataTransfer: { files: [makeImageFile()] },
        });
      });

      expect(screen.getByTestId('drag-overlay')).toBeInTheDocument();
    });

    it('hides drag overlay when dragging leaves the input area', async () => {
      render(
        <ProviderWrapper>
          <BasicChatInput enableImageInput={true} {...defaultProps} />
        </ProviderWrapper>,
      );

      const container = getDragContainer();

      await act(async () => {
        fireEvent.dragOver(container, {
          dataTransfer: { files: [makeImageFile()] },
        });
      });

      expect(screen.getByTestId('drag-overlay')).toBeInTheDocument();

      await act(async () => {
        fireEvent.dragLeave(container, { relatedTarget: document.body });
      });

      expect(screen.queryByTestId('drag-overlay')).not.toBeInTheDocument();
    });

    it('does not show drag overlay when enableImageInput is false', async () => {
      render(
        <ProviderWrapper>
          <BasicChatInput enableImageInput={false} {...defaultProps} />
        </ProviderWrapper>,
      );

      const container = getDragContainer();

      await act(async () => {
        fireEvent.dragOver(container, {
          dataTransfer: { files: [makeImageFile()] },
        });
      });

      expect(screen.queryByTestId('drag-overlay')).not.toBeInTheDocument();
    });

    it('attaches dropped valid image and hides overlay', async () => {
      isSupportedImageFormat.mockReturnValue(true);
      fileToBase64DataUrl.mockResolvedValue('data:image/png;base64,abc');

      render(
        <ProviderWrapper>
          <BasicChatInput enableImageInput={true} {...defaultProps} />
        </ProviderWrapper>,
      );

      const container = getDragContainer();

      await act(async () => {
        fireEvent.dragOver(container, {
          dataTransfer: { files: [makeImageFile()] },
        });
      });

      await act(async () => {
        fireEvent.drop(container, {
          dataTransfer: { files: [makeImageFile()] },
        });
      });

      expect(screen.queryByTestId('drag-overlay')).not.toBeInTheDocument();

      await waitFor(() => {
        expect(screen.getByAltText('photo.png')).toBeInTheDocument();
      });
    });

    it('shows error toast for dropped unsupported image format', async () => {
      isSupportedImageFormat.mockReturnValue(false);

      render(
        <ProviderWrapper>
          <BasicChatInput enableImageInput={true} {...defaultProps} />
        </ProviderWrapper>,
      );

      const container = getDragContainer();

      await act(async () => {
        fireEvent.drop(container, {
          dataTransfer: {
            files: [makeImageFile('bad.pdf', 'application/pdf')],
          },
        });
      });

      expect(toastErrorMock).toHaveBeenCalledWith(
        expect.stringContaining('errors.invalidImageFile'),
      );
      expect(screen.queryByRole('img')).not.toBeInTheDocument();
    });

    it('enables send button after dropping a valid image with no text', async () => {
      isSupportedImageFormat.mockReturnValue(true);
      fileToBase64DataUrl.mockResolvedValue('data:image/png;base64,abc');

      render(
        <ProviderWrapper>
          <BasicChatInput
            enableImageInput={true}
            {...defaultProps}
            content=""
          />
        </ProviderWrapper>,
      );

      expect(screen.getByTestId('send-button')).toBeDisabled();

      const container = getDragContainer();

      await act(async () => {
        fireEvent.drop(container, {
          dataTransfer: { files: [makeImageFile()] },
        });
      });

      await waitFor(() => {
        expect(screen.getByTestId('send-button')).not.toBeDisabled();
      });
    });
  });

  describe('Edge Cases', () => {
    it('handles content with only newlines', async () => {
      const setContentMock = vi.fn();
      const user = userEvent.setup();

      render(
        <ProviderWrapper>
          <BasicChatInput
            enableImageInput={false}
            {...defaultProps}
            setContent={setContentMock}
          />
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
            enableImageInput={false}
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
