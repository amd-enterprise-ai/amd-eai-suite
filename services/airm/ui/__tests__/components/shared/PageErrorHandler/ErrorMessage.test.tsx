// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render, screen } from '@testing-library/react';

import { ErrorCodes } from '@/types/errors';

import ErrorMessage from '@/components/shared/PageErrorHandler/ErrorMessage';

// Mock next-i18next
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// Mock next/router
const mockReplace = vi.fn();
vi.mock('next/router', () => ({
  useRouter: () => ({
    replace: mockReplace,
    asPath: '/current-path',
  }),
}));

// Mock HeroUI components
vi.mock('@heroui/react', () => ({
  Button: ({ children, onPress, color, startContent, ...props }: any) => (
    <button onClick={onPress} data-color={color} {...props}>
      {startContent}
      {children}
    </button>
  ),
}));

// Mock Tabler icons
vi.mock('@tabler/icons-react', () => ({
  IconExclamationCircleFilled: ({ className, size, ...props }: any) => (
    <div data-testid="exclamation-icon" className={className} {...props}>
      Exclamation Icon
    </div>
  ),
  IconChevronDown: ({ className, ...props }: any) => (
    <div data-testid="chevron-down-icon" className={className} {...props}>
      Chevron Down
    </div>
  ),
  IconRefresh: ({ ...props }: any) => (
    <div data-testid="refresh-icon" {...props}>
      Refresh Icon
    </div>
  ),
  IconLoaderQuarter: () => (
    <div data-testid="loader-icon" className="animate-spin" />
  ),
}));

describe('ErrorMessage', () => {
  const mockOnRefresh = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render error component with basic elements', () => {
    render(<ErrorMessage />);

    expect(screen.getByTestId('exclamation-icon')).toBeInTheDocument();
    expect(screen.getByTestId('refresh-icon')).toBeInTheDocument();
    expect(screen.getByText('error.refreshActionLabel')).toBeInTheDocument();
  });

  it('should display translation for known error', () => {
    render(<ErrorMessage code={ErrorCodes.NETWORK_ERROR} />);

    expect(
      screen.getByText(`error.${ErrorCodes.NETWORK_ERROR}.title`),
    ).toBeInTheDocument();
    expect(
      screen.getByText(`error.${ErrorCodes.NETWORK_ERROR}.description`),
    ).toBeInTheDocument();
  });

  it('should display translation for unknown error', () => {
    render(<ErrorMessage code="UNKNOWN_ERROR_CODE" />);

    expect(screen.getByText('error.unknown.title')).toBeInTheDocument();
    expect(screen.getByText('error.unknown.description')).toBeInTheDocument();
  });

  it('should handle refresh functionality', () => {
    render(<ErrorMessage onRefresh={mockOnRefresh} />);

    const refreshButton = screen.getByText('error.refreshActionLabel');
    fireEvent.click(refreshButton);

    expect(mockOnRefresh).toHaveBeenCalledTimes(1);
    expect(mockReplace).not.toHaveBeenCalled();
  });

  it('should not show error details when no message is provided', () => {
    render(<ErrorMessage />);

    expect(
      screen.queryByText('actiosn.showDetails.title'),
    ).not.toBeInTheDocument();
    expect(screen.queryByTestId('chevron-down-icon')).not.toBeInTheDocument();
  });
});
