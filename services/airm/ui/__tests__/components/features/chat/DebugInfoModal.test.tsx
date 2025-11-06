// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { DebugInfo, Message, Source } from '@/types/chat';

import { DebugInfoModal } from '@/components/features/chat/DebugInfoModal';
import ProviderWrapper from '@/__tests__/ProviderWrapper';

import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock the Modal component
vi.mock('@/components/shared/Modal/Modal', () => ({
  Modal: ({ children, onClose, title, subTitle, size }: any) => (
    <div data-testid="modal" data-size={size}>
      <div data-testid="modal-header">
        <h2 data-testid="modal-title">{title}</h2>
        <p data-testid="modal-subtitle">{subTitle}</p>
        <button data-testid="close-button" onClick={onClose}>
          Close
        </button>
      </div>
      <div data-testid="modal-body">{children}</div>
    </div>
  ),
}));

// Mock the MemoizedChatMessage component
vi.mock('@/components/features/chat/MemoizedChatMessage', () => ({
  MemoizedChatMessage: ({ message }: { message: Message }) => (
    <div data-testid="chat-message" data-role={message.role}>
      {message.content}
    </div>
  ),
}));

// Mock HeroUI components
vi.mock('@heroui/react', () => ({
  Accordion: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="accordion">{children}</div>
  ),
  AccordionItem: ({
    title,
    children,
  }: {
    title: string;
    children: React.ReactNode;
  }) => (
    <div data-testid="accordion-item">
      <button
        data-testid={`accordion-toggle-${title.toLowerCase().replace(/\s+/g, '-')}`}
      >
        {title}
      </button>
      <div
        data-testid={`accordion-content-${title.toLowerCase().replace(/\s+/g, '-')}`}
      >
        {children}
      </div>
    </div>
  ),
}));

// Mock next-i18next
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'debugInfoModal.title': 'Debug Information',
        'debugInfoModal.subTitle':
          'Detailed debugging data for this conversation',
        'debugInfoModal.ragDocumentsTitle': 'RAG Documents',
        'debugInfoModal.ragDocumentsDescription':
          'Documents retrieved from the knowledge base',
        'debugInfoModal.promptsTitle': 'Prompts',
        'debugInfoModal.promptsDescription':
          'System and user prompts used in this conversation',
        'debugInfoModal.tokenUsageTitle': 'Token Usage',
        'debugInfoModal.promptTokens': 'Prompt Tokens:',
        'debugInfoModal.completionTokens': 'Completion Tokens:',
        'debugInfoModal.totalTokens': 'Total Tokens:',
        'debugInfoModal.noSources': 'No sources available',
        'debugInfoModal.noPromptMessages': 'No prompt messages available',
        'debugInfoModal.noTokenUsage': 'Token usage information not available',
      };
      return translations[key] || key;
    },
  }),
}));

describe('DebugInfoModal Component', () => {
  const mockSources: Source[] = [
    {
      url: 'https://example.com/doc1',
      sourceId: 'document-1',
      text: 'This is the content of the first retrieved document',
      score: 0.95,
    },
    {
      url: 'https://example.com/doc2',
      sourceId: 'document-2',
      text: 'This is the content of the second retrieved document',
      score: 0.87,
    },
  ];

  const mockMessages: Message[] = [
    {
      role: 'system',
      content: 'You are a helpful assistant.',
    },
    {
      role: 'user',
      content: 'What is the weather like today?',
    },
    {
      role: 'assistant',
      content: 'I can help you with weather information.',
    },
  ];

  const mockDebugInfo: DebugInfo = {
    messages: mockMessages,
    sources: mockSources,
    usage: {
      prompt_tokens: 150,
      completion_tokens: 75,
      total_tokens: 225,
    },
  };

  const defaultProps = {
    debugInfo: mockDebugInfo,
    onClose: vi.fn(),
    isOpen: true,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders the modal when isOpen is true', () => {
      render(
        <ProviderWrapper>
          <DebugInfoModal {...defaultProps} />
        </ProviderWrapper>,
      );

      expect(screen.getByTestId('modal')).toBeInTheDocument();
      expect(screen.getByTestId('modal-title')).toHaveTextContent(
        'Debug Information',
      );
      expect(screen.getByTestId('modal-subtitle')).toHaveTextContent(
        'Detailed debugging data for this conversation',
      );
    });

    it('does not render the modal when isOpen is false', () => {
      render(
        <ProviderWrapper>
          <DebugInfoModal {...defaultProps} isOpen={false} />
        </ProviderWrapper>,
      );

      expect(screen.queryByTestId('modal')).not.toBeInTheDocument();
    });

    it('renders with correct modal size', () => {
      render(
        <ProviderWrapper>
          <DebugInfoModal {...defaultProps} />
        </ProviderWrapper>,
      );

      expect(screen.getByTestId('modal')).toHaveAttribute('data-size', '3xl');
    });

    it('renders accordion with all three sections', () => {
      render(
        <ProviderWrapper>
          <DebugInfoModal {...defaultProps} />
        </ProviderWrapper>,
      );

      expect(screen.getByTestId('accordion')).toBeInTheDocument();
      expect(
        screen.getByTestId('accordion-toggle-rag-documents'),
      ).toHaveTextContent('RAG Documents');
      expect(screen.getByTestId('accordion-toggle-prompts')).toHaveTextContent(
        'Prompts',
      );
      expect(
        screen.getByTestId('accordion-toggle-token-usage'),
      ).toHaveTextContent('Token Usage');
    });
  });

  describe('Close Functionality', () => {
    it('calls onClose when close button is clicked', async () => {
      const onCloseMock = vi.fn();
      const user = userEvent.setup();

      render(
        <ProviderWrapper>
          <DebugInfoModal {...defaultProps} onClose={onCloseMock} />
        </ProviderWrapper>,
      );

      const closeButton = screen.getByTestId('close-button');
      await user.click(closeButton);

      expect(onCloseMock).toHaveBeenCalled();
    });
  });

  describe('RAG Documents Section', () => {
    it('renders RAG documents section with sources', () => {
      render(
        <ProviderWrapper>
          <DebugInfoModal {...defaultProps} />
        </ProviderWrapper>,
      );

      const ragContent = screen.getByTestId('accordion-content-rag-documents');
      expect(ragContent).toBeInTheDocument();

      // Check for description
      expect(
        screen.getByText('Documents retrieved from the knowledge base'),
      ).toBeInTheDocument();

      // Check for sources
      expect(screen.getByText('1. document-1')).toBeInTheDocument();
      expect(screen.getByText('2. document-2')).toBeInTheDocument();
      expect(screen.getByText('https://example.com/doc1')).toBeInTheDocument();
      expect(screen.getByText('https://example.com/doc2')).toBeInTheDocument();
    });

    it('renders source content and scores', () => {
      render(
        <ProviderWrapper>
          <DebugInfoModal {...defaultProps} />
        </ProviderWrapper>,
      );

      expect(
        screen.getByText('This is the content of the first retrieved document'),
      ).toBeInTheDocument();
      expect(
        screen.getByText(
          'This is the content of the second retrieved document',
        ),
      ).toBeInTheDocument();
      expect(screen.getByText('0.95')).toBeInTheDocument();
      expect(screen.getByText('0.87')).toBeInTheDocument();
    });

    it('renders sources with zero score correctly', () => {
      const debugInfoWithZeroScore: DebugInfo = {
        ...mockDebugInfo,
        sources: [
          {
            url: 'https://example.com/doc-zero',
            sourceId: 'document-zero',
            text: 'Document with zero score',
            score: 0,
          },
        ],
      };

      render(
        <ProviderWrapper>
          <DebugInfoModal
            {...defaultProps}
            debugInfo={debugInfoWithZeroScore}
          />
        </ProviderWrapper>,
      );

      expect(screen.getByText('0.00')).toBeInTheDocument();
    });

    it('renders N/A for sources without score', () => {
      const debugInfoWithoutScore: DebugInfo = {
        ...mockDebugInfo,
        sources: [
          {
            url: 'https://example.com/doc-no-score',
            sourceId: 'document-no-score',
            text: 'Document without score',
            // No score property
          },
        ],
      };

      render(
        <ProviderWrapper>
          <DebugInfoModal {...defaultProps} debugInfo={debugInfoWithoutScore} />
        </ProviderWrapper>,
      );

      expect(screen.getByText('N/A')).toBeInTheDocument();
    });

    it('renders empty sources section when sources array is empty', () => {
      const debugInfoWithoutSources: DebugInfo = {
        ...mockDebugInfo,
        sources: [],
      };

      render(
        <ProviderWrapper>
          <DebugInfoModal
            {...defaultProps}
            debugInfo={debugInfoWithoutSources}
          />
        </ProviderWrapper>,
      );

      const ragContent = screen.getByTestId('accordion-content-rag-documents');
      expect(ragContent).toBeInTheDocument();

      // Should show description but no sources (since the array is empty but truthy)
      expect(
        screen.getByText('Documents retrieved from the knowledge base'),
      ).toBeInTheDocument();

      // Should not show any source items
      expect(screen.queryByText(/document-/)).not.toBeInTheDocument();
    });

    it('renders no sources message when sources is falsy', () => {
      const debugInfoWithoutSources: DebugInfo = {
        ...mockDebugInfo,
        sources: undefined as any,
      };

      render(
        <ProviderWrapper>
          <DebugInfoModal
            {...defaultProps}
            debugInfo={debugInfoWithoutSources}
          />
        </ProviderWrapper>,
      );

      expect(screen.getByText('No sources available')).toBeInTheDocument();
    });

    it('renders source links as clickable', () => {
      render(
        <ProviderWrapper>
          <DebugInfoModal {...defaultProps} />
        </ProviderWrapper>,
      );

      const link1 = screen.getByRole('link', {
        name: 'https://example.com/doc1',
      });
      const link2 = screen.getByRole('link', {
        name: 'https://example.com/doc2',
      });

      expect(link1).toHaveAttribute('href', 'https://example.com/doc1');
      expect(link2).toHaveAttribute('href', 'https://example.com/doc2');
    });
  });

  describe('Prompts Section', () => {
    it('renders prompts section with messages', () => {
      render(
        <ProviderWrapper>
          <DebugInfoModal {...defaultProps} />
        </ProviderWrapper>,
      );

      const promptsContent = screen.getByTestId('accordion-content-prompts');
      expect(promptsContent).toBeInTheDocument();

      // Check for description
      expect(
        screen.getByText('System and user prompts used in this conversation'),
      ).toBeInTheDocument();

      // Check for chat messages
      const chatMessages = screen.getAllByTestId('chat-message');
      expect(chatMessages).toHaveLength(3);

      expect(chatMessages[0]).toHaveAttribute('data-role', 'system');
      expect(chatMessages[1]).toHaveAttribute('data-role', 'user');
      expect(chatMessages[2]).toHaveAttribute('data-role', 'assistant');
    });

    it('renders message content correctly', () => {
      render(
        <ProviderWrapper>
          <DebugInfoModal {...defaultProps} />
        </ProviderWrapper>,
      );

      expect(
        screen.getByText('You are a helpful assistant.'),
      ).toBeInTheDocument();
      expect(
        screen.getByText('What is the weather like today?'),
      ).toBeInTheDocument();
      expect(
        screen.getByText('I can help you with weather information.'),
      ).toBeInTheDocument();
    });

    it('renders empty messages section when messages array is empty', () => {
      const debugInfoWithoutMessages: DebugInfo = {
        ...mockDebugInfo,
        messages: [],
      };

      render(
        <ProviderWrapper>
          <DebugInfoModal
            {...defaultProps}
            debugInfo={debugInfoWithoutMessages}
          />
        </ProviderWrapper>,
      );

      const promptsContent = screen.getByTestId('accordion-content-prompts');
      expect(promptsContent).toBeInTheDocument();

      // Should show description but no messages (since the array is empty but truthy)
      expect(
        screen.getByText('System and user prompts used in this conversation'),
      ).toBeInTheDocument();

      // Should not show any chat messages
      expect(screen.queryAllByTestId('chat-message')).toHaveLength(0);
    });

    it('renders no messages when messages is falsy', () => {
      const debugInfoWithoutMessages: DebugInfo = {
        ...mockDebugInfo,
        messages: undefined as any,
      };

      render(
        <ProviderWrapper>
          <DebugInfoModal
            {...defaultProps}
            debugInfo={debugInfoWithoutMessages}
          />
        </ProviderWrapper>,
      );

      expect(
        screen.getByText('No prompt messages available'),
      ).toBeInTheDocument();
    });
  });

  describe('Token Usage Section', () => {
    it('renders token usage information when available', () => {
      render(
        <ProviderWrapper>
          <DebugInfoModal {...defaultProps} />
        </ProviderWrapper>,
      );

      const tokenUsageContent = screen.getByTestId(
        'accordion-content-token-usage',
      );
      expect(tokenUsageContent).toBeInTheDocument();

      expect(screen.getByText('Prompt Tokens:')).toBeInTheDocument();
      expect(screen.getByText('150')).toBeInTheDocument();

      expect(screen.getByText('Completion Tokens:')).toBeInTheDocument();
      expect(screen.getByText('75')).toBeInTheDocument();

      expect(screen.getByText('Total Tokens:')).toBeInTheDocument();
      expect(screen.getByText('225')).toBeInTheDocument();
    });

    it('renders no token usage message when usage is not available', () => {
      const debugInfoWithoutUsage: DebugInfo = {
        ...mockDebugInfo,
        usage: undefined,
      };

      render(
        <ProviderWrapper>
          <DebugInfoModal {...defaultProps} debugInfo={debugInfoWithoutUsage} />
        </ProviderWrapper>,
      );

      expect(
        screen.getByText('Token usage information not available'),
      ).toBeInTheDocument();
    });

    it('renders token usage with zero values correctly', () => {
      const debugInfoWithZeroUsage: DebugInfo = {
        ...mockDebugInfo,
        usage: {
          prompt_tokens: 0,
          completion_tokens: 0,
          total_tokens: 0,
        },
      };

      render(
        <ProviderWrapper>
          <DebugInfoModal
            {...defaultProps}
            debugInfo={debugInfoWithZeroUsage}
          />
        </ProviderWrapper>,
      );

      // Should render all zeros
      const zeroElements = screen.getAllByText('0');
      expect(zeroElements).toHaveLength(3);
    });
  });

  describe('Edge Cases and Error Handling', () => {
    it('handles empty debugInfo gracefully', () => {
      const emptyDebugInfo: DebugInfo = {
        messages: [],
        sources: [],
      };

      render(
        <ProviderWrapper>
          <DebugInfoModal {...defaultProps} debugInfo={emptyDebugInfo} />
        </ProviderWrapper>,
      );

      // Should render all sections but with empty content
      expect(
        screen.getByText('Documents retrieved from the knowledge base'),
      ).toBeInTheDocument();
      expect(
        screen.getByText('System and user prompts used in this conversation'),
      ).toBeInTheDocument();
      expect(
        screen.getByText('Token usage information not available'),
      ).toBeInTheDocument();

      // Should not have any sources or messages
      expect(screen.queryAllByTestId('chat-message')).toHaveLength(0);
      expect(screen.queryByText(/document-/)).not.toBeInTheDocument();
    });

    it('handles debugInfo with only some properties', () => {
      const partialDebugInfo: DebugInfo = {
        messages: mockMessages,
        sources: [],
        // No usage
      };

      render(
        <ProviderWrapper>
          <DebugInfoModal {...defaultProps} debugInfo={partialDebugInfo} />
        </ProviderWrapper>,
      );

      // Should show messages
      expect(screen.getAllByTestId('chat-message')).toHaveLength(3);

      // Should show empty sources section (empty array is truthy)
      expect(
        screen.getByText('Documents retrieved from the knowledge base'),
      ).toBeInTheDocument();
      expect(screen.queryByText(/document-/)).not.toBeInTheDocument();

      // Should show no token usage
      expect(
        screen.getByText('Token usage information not available'),
      ).toBeInTheDocument();
    });

    it('handles very long source text without breaking layout', () => {
      const longText =
        'This is a very long source text that should be handled properly by the component. '.repeat(
          20,
        );
      const debugInfoWithLongText: DebugInfo = {
        ...mockDebugInfo,
        sources: [
          {
            url: 'https://example.com/long-doc',
            sourceId: 'long-document',
            text: longText,
            score: 0.5,
          },
        ],
      };

      render(
        <ProviderWrapper>
          <DebugInfoModal {...defaultProps} debugInfo={debugInfoWithLongText} />
        </ProviderWrapper>,
      );

      // Check that the component renders without breaking and shows the source
      expect(screen.getByText('1. long-document')).toBeInTheDocument();
      expect(
        screen.getByText('https://example.com/long-doc'),
      ).toBeInTheDocument();
      // For very long text, just check that part of it is there using a substring
      expect(
        screen.getByText(
          /This is a very long source text that should be handled properly by the component/,
        ),
      ).toBeInTheDocument();
    });

    it('handles sources with special characters in URLs', () => {
      const debugInfoWithSpecialChars: DebugInfo = {
        ...mockDebugInfo,
        sources: [
          {
            url: 'https://example.com/path/file%20with%20spaces?query=test&other=value#section',
            sourceId: 'special-chars-doc',
            text: 'Document with special URL',
            score: 0.8,
          },
        ],
      };

      render(
        <ProviderWrapper>
          <DebugInfoModal
            {...defaultProps}
            debugInfo={debugInfoWithSpecialChars}
          />
        </ProviderWrapper>,
      );

      const link = screen.getByRole('link');
      expect(link).toHaveAttribute(
        'href',
        'https://example.com/path/file%20with%20spaces?query=test&other=value#section',
      );
    });

    it('handles large token usage values', () => {
      const debugInfoWithLargeUsage: DebugInfo = {
        ...mockDebugInfo,
        usage: {
          prompt_tokens: 1000000,
          completion_tokens: 500000,
          total_tokens: 1500000,
        },
      };

      render(
        <ProviderWrapper>
          <DebugInfoModal
            {...defaultProps}
            debugInfo={debugInfoWithLargeUsage}
          />
        </ProviderWrapper>,
      );

      expect(screen.getByText('1000000')).toBeInTheDocument();
      expect(screen.getByText('500000')).toBeInTheDocument();
      expect(screen.getByText('1500000')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('provides proper structure for screen readers', () => {
      render(
        <ProviderWrapper>
          <DebugInfoModal {...defaultProps} />
        </ProviderWrapper>,
      );

      // Modal should have proper title
      expect(screen.getByTestId('modal-title')).toBeInTheDocument();

      // Accordion sections should have proper labels
      expect(
        screen.getByTestId('accordion-toggle-rag-documents'),
      ).toBeInTheDocument();
      expect(
        screen.getByTestId('accordion-toggle-prompts'),
      ).toBeInTheDocument();
      expect(
        screen.getByTestId('accordion-toggle-token-usage'),
      ).toBeInTheDocument();

      // Links should be properly accessible
      const links = screen.getAllByRole('link');
      links.forEach((link) => {
        expect(link).toHaveAttribute('href');
      });
    });
  });

  describe('Performance', () => {
    it('handles large number of sources efficiently', () => {
      const manySources: Source[] = Array.from({ length: 100 }, (_, i) => ({
        url: `https://example.com/doc${i}`,
        sourceId: `document-${i}`,
        text: `Content of document ${i}`,
        score: Math.random(),
      }));

      const debugInfoWithManySources: DebugInfo = {
        ...mockDebugInfo,
        sources: manySources,
      };

      expect(() =>
        render(
          <ProviderWrapper>
            <DebugInfoModal
              {...defaultProps}
              debugInfo={debugInfoWithManySources}
            />
          </ProviderWrapper>,
        ),
      ).not.toThrow();

      // Should render all sources
      expect(screen.getByText('1. document-0')).toBeInTheDocument();
      expect(screen.getByText('100. document-99')).toBeInTheDocument();
    });

    it('handles large number of messages efficiently', () => {
      const manyMessages: Message[] = Array.from({ length: 50 }, (_, i) => ({
        role: (i % 2 === 0 ? 'user' : 'assistant') as 'user' | 'assistant',
        content: `Message ${i} content`,
      }));

      const debugInfoWithManyMessages: DebugInfo = {
        ...mockDebugInfo,
        messages: manyMessages,
      };

      expect(() =>
        render(
          <ProviderWrapper>
            <DebugInfoModal
              {...defaultProps}
              debugInfo={debugInfoWithManyMessages}
            />
          </ProviderWrapper>,
        ),
      ).not.toThrow();

      // Should render all messages
      const chatMessages = screen.getAllByTestId('chat-message');
      expect(chatMessages).toHaveLength(50);
    });
  });
});
