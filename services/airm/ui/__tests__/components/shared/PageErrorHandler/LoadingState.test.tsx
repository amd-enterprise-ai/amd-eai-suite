// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';

import LoadingState from '@/components/shared/PageErrorHandler/LoadingState';

// Mock next-i18next
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// Mock HeroUI components
vi.mock('@heroui/react', () => ({
  Spinner: ({ size, color, ...props }: any) => (
    <div data-testid="spinner" data-size={size} data-color={color} {...props}>
      Loading spinner
    </div>
  ),
}));

describe('LoadingState', () => {
  it('should render the loading spinner', () => {
    render(<LoadingState />);

    const spinner = screen.getByTestId('spinner');
    expect(spinner).toBeInTheDocument();
    expect(spinner).toHaveAttribute('data-size', 'md');
    expect(spinner).toHaveAttribute('data-color', 'default');
  });

  it('should render the loading text with translation', () => {
    render(<LoadingState />);

    const loadingText = screen.getByText('charts.loading');
    expect(loadingText).toBeInTheDocument();
  });

  it('should have proper styling classes', () => {
    render(<LoadingState />);

    const container = screen.getByText('charts.loading').closest('div');
    expect(container).toHaveClass('text-center');

    const outerContainer = container?.parentElement;
    expect(outerContainer).toHaveClass(
      'w-full',
      'h-full',
      'flex',
      'justify-center',
      'items-center',
    );
  });

  it('should render loading text with proper styling', () => {
    render(<LoadingState />);

    const loadingText = screen.getByText('charts.loading');
    expect(loadingText).toHaveClass('text-default-500');
  });

  it('should display both spinner and text', () => {
    render(<LoadingState />);

    expect(screen.getByTestId('spinner')).toBeInTheDocument();
    expect(screen.getByText('charts.loading')).toBeInTheDocument();
  });
});
