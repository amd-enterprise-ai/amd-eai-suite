// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';

import ChatInfoCard from '@/components/features/chat/ChatInfoCard';
import ProviderWrapper from '@/__tests__/ProviderWrapper';

import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock HeroUI components
vi.mock('@heroui/react', () => ({
  Card: ({
    children,
    className,
  }: {
    children: React.ReactNode;
    className: string;
  }) => (
    <div data-testid="card" className={className}>
      {children}
    </div>
  ),
  CardBody: ({
    children,
    className,
  }: {
    children: React.ReactNode;
    className: string;
  }) => (
    <div data-testid="card-body" className={className}>
      {children}
    </div>
  ),
}));

// Mock Tabler icons
vi.mock('@tabler/icons-react', () => ({
  IconBubbleText: ({
    size,
    className,
  }: {
    size: number;
    className: string;
  }) => (
    <svg data-testid="bubble-text-icon" data-size={size} className={className}>
      <title>Bubble Text Icon</title>
    </svg>
  ),
  IconGitCompare: ({
    size,
    className,
  }: {
    size: number;
    className: string;
  }) => (
    <svg data-testid="git-compare-icon" data-size={size} className={className}>
      <title>Git Compare Icon</title>
    </svg>
  ),
}));

// Mock next-i18next
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        // Chat mode translations
        'chat.title': 'Chat Mode',
        'chat.description':
          'Start a conversation with your AI assistant. Ask questions, get help, or have a discussion.',
        'chat.tips.tip1': 'Try asking specific questions for better responses',
        'chat.tips.tip2': 'Use clear and concise language for best results',

        // Compare mode translations
        'compare.title': 'Compare Mode',
        'compare.description':
          'Compare responses from multiple AI models side by side to find the best answer.',
        'compare.tips.tip1':
          'Select different models to see varied perspectives',
        'compare.tips.tip2': 'Compare outputs to make informed decisions',
      };
      return translations[key] || key;
    },
  }),
}));

describe('ChatInfoCard Component', () => {
  describe('Chat Mode', () => {
    it('renders chat mode correctly', () => {
      render(
        <ProviderWrapper>
          <ChatInfoCard mode="chat" />
        </ProviderWrapper>,
      );

      // Check that the card is rendered
      expect(screen.getByTestId('card')).toBeInTheDocument();
      expect(screen.getByTestId('card-body')).toBeInTheDocument();

      // Check for chat mode specific content
      expect(screen.getByText('Chat Mode')).toBeInTheDocument();
      expect(
        screen.getByText(
          'Start a conversation with your AI assistant. Ask questions, get help, or have a discussion.',
        ),
      ).toBeInTheDocument();

      // Check for chat icon
      expect(screen.getByTestId('bubble-text-icon')).toBeInTheDocument();
      expect(screen.queryByTestId('git-compare-icon')).not.toBeInTheDocument();
    });

    it('renders chat mode tips correctly', () => {
      render(
        <ProviderWrapper>
          <ChatInfoCard mode="chat" />
        </ProviderWrapper>,
      );

      expect(
        screen.getByText('Try asking specific questions for better responses'),
      ).toBeInTheDocument();
      expect(
        screen.getByText('Use clear and concise language for best results'),
      ).toBeInTheDocument();
    });

    it('renders chat icon with correct properties', () => {
      render(
        <ProviderWrapper>
          <ChatInfoCard mode="chat" />
        </ProviderWrapper>,
      );

      const chatIcon = screen.getByTestId('bubble-text-icon');
      expect(chatIcon).toHaveAttribute('data-size', '28');
      expect(chatIcon).toHaveClass('text-primary-600', 'dark:text-primary-300');
    });
  });

  describe('Compare Mode', () => {
    it('renders compare mode correctly', () => {
      render(
        <ProviderWrapper>
          <ChatInfoCard mode="compare" />
        </ProviderWrapper>,
      );

      // Check that the card is rendered
      expect(screen.getByTestId('card')).toBeInTheDocument();
      expect(screen.getByTestId('card-body')).toBeInTheDocument();

      // Check for compare mode specific content
      expect(screen.getByText('Compare Mode')).toBeInTheDocument();
      expect(
        screen.getByText(
          'Compare responses from multiple AI models side by side to find the best answer.',
        ),
      ).toBeInTheDocument();

      // Check for compare icon
      expect(screen.getByTestId('git-compare-icon')).toBeInTheDocument();
      expect(screen.queryByTestId('bubble-text-icon')).not.toBeInTheDocument();
    });

    it('renders compare mode tips correctly', () => {
      render(
        <ProviderWrapper>
          <ChatInfoCard mode="compare" />
        </ProviderWrapper>,
      );

      expect(
        screen.getByText('Select different models to see varied perspectives'),
      ).toBeInTheDocument();
      expect(
        screen.getByText('Compare outputs to make informed decisions'),
      ).toBeInTheDocument();
    });

    it('renders compare icon with correct properties', () => {
      render(
        <ProviderWrapper>
          <ChatInfoCard mode="compare" />
        </ProviderWrapper>,
      );

      const compareIcon = screen.getByTestId('git-compare-icon');
      expect(compareIcon).toHaveAttribute('data-size', '28');
      expect(compareIcon).toHaveClass(
        'text-primary-600',
        'dark:text-primary-300',
      );
    });
  });

  describe('Styling and Layout', () => {
    it('applies correct CSS classes to the card', () => {
      render(
        <ProviderWrapper>
          <ChatInfoCard mode="chat" />
        </ProviderWrapper>,
      );

      const card = screen.getByTestId('card');
      expect(card).toHaveClass(
        'hidden',
        'md:block',
        'fixed',
        'top-1/2',
        'max-w-[600px]',
        'mx-8',
        'p-8',
        'shadow-none',
        '-translate-y-1/2',
        'border',
        'border-default-200',
        'dark:border-default-300',
      );
    });

    it('applies correct CSS classes to the card body', () => {
      render(
        <ProviderWrapper>
          <ChatInfoCard mode="chat" />
        </ProviderWrapper>,
      );

      const cardBody = screen.getByTestId('card-body');
      expect(cardBody).toHaveClass('flex', 'flex-col', 'gap-3', 'items-start');
    });

    it('renders icon container with correct styling', () => {
      render(
        <ProviderWrapper>
          <ChatInfoCard mode="chat" />
        </ProviderWrapper>,
      );

      // The icon container should be present (though we can't test exact classes easily)
      const iconContainer = screen
        .getByTestId('bubble-text-icon')
        .closest('span');
      expect(iconContainer).toBeInTheDocument();
    });

    it('renders title with correct styling classes', () => {
      render(
        <ProviderWrapper>
          <ChatInfoCard mode="chat" />
        </ProviderWrapper>,
      );

      const title = screen.getByRole('heading', { level: 2 });
      expect(title).toHaveClass('font-bold', 'text-2xl', 'text-default-800');
      expect(title).toHaveTextContent('Chat Mode');
    });

    it('renders list items correctly', () => {
      render(
        <ProviderWrapper>
          <ChatInfoCard mode="chat" />
        </ProviderWrapper>,
      );

      const listItems = screen.getAllByRole('listitem');
      expect(listItems).toHaveLength(2);
    });

    it('renders unordered list with correct styling', () => {
      render(
        <ProviderWrapper>
          <ChatInfoCard mode="chat" />
        </ProviderWrapper>,
      );

      const list = screen.getByRole('list');
      expect(list).toHaveClass(
        'list-disc',
        'pl-4',
        'text-default-600',
        'text-sm',
        'space-y-1',
        'mb-1',
      );
    });
  });

  describe('Accessibility', () => {
    it('has proper heading structure', () => {
      render(
        <ProviderWrapper>
          <ChatInfoCard mode="chat" />
        </ProviderWrapper>,
      );

      const heading = screen.getByRole('heading', { level: 2 });
      expect(heading).toBeInTheDocument();
      expect(heading).toHaveTextContent('Chat Mode');
    });

    it('has accessible list structure', () => {
      render(
        <ProviderWrapper>
          <ChatInfoCard mode="chat" />
        </ProviderWrapper>,
      );

      const list = screen.getByRole('list');
      expect(list).toBeInTheDocument();

      const listItems = screen.getAllByRole('listitem');
      expect(listItems).toHaveLength(2);
    });

    it('icons have accessible titles', () => {
      render(
        <ProviderWrapper>
          <ChatInfoCard mode="chat" />
        </ProviderWrapper>,
      );

      expect(screen.getByTitle('Bubble Text Icon')).toBeInTheDocument();
    });

    it('compare mode icons have accessible titles', () => {
      render(
        <ProviderWrapper>
          <ChatInfoCard mode="compare" />
        </ProviderWrapper>,
      );

      expect(screen.getByTitle('Git Compare Icon')).toBeInTheDocument();
    });
  });

  describe('Responsive Design', () => {
    it('is hidden on mobile devices', () => {
      render(
        <ProviderWrapper>
          <ChatInfoCard mode="chat" />
        </ProviderWrapper>,
      );

      const card = screen.getByTestId('card');
      expect(card).toHaveClass('hidden', 'md:block');
    });

    it('has responsive maximum width', () => {
      render(
        <ProviderWrapper>
          <ChatInfoCard mode="chat" />
        </ProviderWrapper>,
      );

      const card = screen.getByTestId('card');
      expect(card).toHaveClass('max-w-[600px]');
    });

    it('has proper positioning for different screen sizes', () => {
      render(
        <ProviderWrapper>
          <ChatInfoCard mode="chat" />
        </ProviderWrapper>,
      );

      const card = screen.getByTestId('card');
      expect(card).toHaveClass('fixed', 'top-1/2', '-translate-y-1/2', 'mx-8');
    });
  });

  describe('Translation Integration', () => {
    it('displays correct translated content for chat mode', () => {
      render(
        <ProviderWrapper>
          <ChatInfoCard mode="chat" />
        </ProviderWrapper>,
      );

      // Verify that the translated content is displayed
      expect(screen.getByText('Chat Mode')).toBeInTheDocument();
      expect(
        screen.getByText(
          'Start a conversation with your AI assistant. Ask questions, get help, or have a discussion.',
        ),
      ).toBeInTheDocument();
      expect(
        screen.getByText('Try asking specific questions for better responses'),
      ).toBeInTheDocument();
      expect(
        screen.getByText('Use clear and concise language for best results'),
      ).toBeInTheDocument();
    });

    it('displays correct translated content for compare mode', () => {
      render(
        <ProviderWrapper>
          <ChatInfoCard mode="compare" />
        </ProviderWrapper>,
      );

      // Verify that the translated content is displayed
      expect(screen.getByText('Compare Mode')).toBeInTheDocument();
      expect(
        screen.getByText(
          'Compare responses from multiple AI models side by side to find the best answer.',
        ),
      ).toBeInTheDocument();
      expect(
        screen.getByText('Select different models to see varied perspectives'),
      ).toBeInTheDocument();
      expect(
        screen.getByText('Compare outputs to make informed decisions'),
      ).toBeInTheDocument();
    });

    it('uses the translation hook correctly', () => {
      // This test verifies that the component uses useTranslation
      // The mock is already set up at the top level
      render(
        <ProviderWrapper>
          <ChatInfoCard mode="chat" />
        </ProviderWrapper>,
      );

      // If the translation system is working, we should see the translated content
      expect(screen.getByText('Chat Mode')).toBeInTheDocument();
      expect(
        screen.getByText(
          'Start a conversation with your AI assistant. Ask questions, get help, or have a discussion.',
        ),
      ).toBeInTheDocument();
    });
  });

  describe('Mode Switching', () => {
    it('switches content when mode changes from chat to compare', () => {
      const { rerender } = render(
        <ProviderWrapper>
          <ChatInfoCard mode="chat" />
        </ProviderWrapper>,
      );

      // Initially shows chat content
      expect(screen.getByText('Chat Mode')).toBeInTheDocument();
      expect(screen.getByTestId('bubble-text-icon')).toBeInTheDocument();

      // Rerender with compare mode
      rerender(
        <ProviderWrapper>
          <ChatInfoCard mode="compare" />
        </ProviderWrapper>,
      );

      // Now shows compare content
      expect(screen.getByText('Compare Mode')).toBeInTheDocument();
      expect(screen.getByTestId('git-compare-icon')).toBeInTheDocument();
      expect(screen.queryByTestId('bubble-text-icon')).not.toBeInTheDocument();
    });

    it('updates tips when mode changes', () => {
      const { rerender } = render(
        <ProviderWrapper>
          <ChatInfoCard mode="chat" />
        </ProviderWrapper>,
      );

      // Initially shows chat tips
      expect(
        screen.getByText('Try asking specific questions for better responses'),
      ).toBeInTheDocument();

      // Rerender with compare mode
      rerender(
        <ProviderWrapper>
          <ChatInfoCard mode="compare" />
        </ProviderWrapper>,
      );

      // Now shows compare tips
      expect(
        screen.getByText('Select different models to see varied perspectives'),
      ).toBeInTheDocument();
      expect(
        screen.queryByText(
          'Try asking specific questions for better responses',
        ),
      ).not.toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('renders without crashing with minimal props', () => {
      expect(() =>
        render(
          <ProviderWrapper>
            <ChatInfoCard mode="chat" />
          </ProviderWrapper>,
        ),
      ).not.toThrow();
    });

    it('handles undefined mode gracefully', () => {
      // This test ensures the component doesn't break with unexpected props
      expect(() =>
        render(
          <ProviderWrapper>
            <ChatInfoCard mode={'invalid' as any} />
          </ProviderWrapper>,
        ),
      ).not.toThrow();
    });
  });

  describe('Component Structure', () => {
    it('maintains proper HTML structure', () => {
      render(
        <ProviderWrapper>
          <ChatInfoCard mode="chat" />
        </ProviderWrapper>,
      );

      // Card contains CardBody
      const card = screen.getByTestId('card');
      const cardBody = screen.getByTestId('card-body');
      expect(card).toContainElement(cardBody);

      // CardBody contains header section
      const heading = screen.getByRole('heading', { level: 2 });
      expect(cardBody).toContainElement(heading);

      // CardBody contains list
      const list = screen.getByRole('list');
      expect(cardBody).toContainElement(list);
    });

    it('renders flex layout correctly', () => {
      render(
        <ProviderWrapper>
          <ChatInfoCard mode="chat" />
        </ProviderWrapper>,
      );

      // The header section should contain icon and title
      const heading = screen.getByRole('heading', { level: 2 });
      const icon = screen.getByTestId('bubble-text-icon');

      // Both should be in the same parent container
      const headerContainer = heading.closest('div');
      expect(headerContainer).toContainElement(icon);
      expect(headerContainer).toContainElement(heading);
    });
  });
});
