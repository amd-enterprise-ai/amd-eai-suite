// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render, screen } from '@testing-library/react';

import { ErrorCodes } from '@amdenterpriseai/types';

import { ErrorMessage } from '@/components/shared/PageErrorHandler/ErrorMessage';

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
  Button: ({
    children,
    onPress,
    color,
    startContent,
    endContent,
    ...props
  }: any) => (
    <button onClick={onPress} data-color={color} {...props}>
      {startContent}
      {children}
      {endContent}
    </button>
  ),
}));

// Mock Tabler icons with specific test IDs for testing
vi.mock('@tabler/icons-react', async () => {
  const actual = await vi.importActual<typeof import('@tabler/icons-react')>(
    '@tabler/icons-react',
  );
  return {
    ...actual,
    // Override only the icons we need specific test IDs for
    IconAlertTriangle: ({ className, size, ...props }: any) => (
      <div
        data-testid="exclamation-icon"
        className={className}
        data-size={size}
        {...props}
      >
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
    IconLoaderQuarter: ({ className, ...props }: any) => (
      <div
        data-testid="loader-icon"
        className={`animate-spin ${className || ''}`}
        {...props}
      />
    ),
  };
});

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
    render(<ErrorMessage code={ErrorCodes.FETCH_FAILED} />);

    expect(
      screen.getByText(`error.${ErrorCodes.FETCH_FAILED}.title`),
    ).toBeInTheDocument();
    expect(
      screen.getByText(`error.${ErrorCodes.FETCH_FAILED}.description`),
    ).toBeInTheDocument();
  });

  it('should display translation for unknown error', () => {
    render(<ErrorMessage code="UNKNOWN_ERROR_CODE" />);

    expect(screen.getByText('error.unknown.title')).toBeInTheDocument();
    expect(screen.getByText('error.unknown.description')).toBeInTheDocument();
  });

  it('should handle refresh functionality with onRefresh callback', () => {
    render(<ErrorMessage onRefresh={mockOnRefresh} />);

    const refreshButton = screen.getByText('error.refreshActionLabel');
    fireEvent.click(refreshButton);

    expect(mockOnRefresh).toHaveBeenCalledTimes(1);
    expect(mockReplace).not.toHaveBeenCalled();
  });

  it('should use router.replace when onRefresh is not provided', () => {
    render(<ErrorMessage />);

    const refreshButton = screen.getByText('error.refreshActionLabel');
    fireEvent.click(refreshButton);

    expect(mockReplace).toHaveBeenCalledWith('/current-path');
    expect(mockOnRefresh).not.toHaveBeenCalled();
  });

  it('should not show error details when no message is provided', () => {
    render(<ErrorMessage />);

    expect(
      screen.queryByText('actions.showDetails.title'),
    ).not.toBeInTheDocument();
    expect(screen.queryByTestId('chevron-down-icon')).not.toBeInTheDocument();
  });

  it('should show and toggle error details when message is provided', () => {
    render(<ErrorMessage message="Detailed error message" />);

    const showDetailsButton = screen.getByText('actions.showDetails.title');
    expect(showDetailsButton).toBeInTheDocument();
    expect(screen.getByTestId('chevron-down-icon')).toBeInTheDocument();

    // Initially details should be hidden (rendered but not visible via CSS)
    expect(
      screen.queryByText('error.label: Detailed error message'),
    ).toBeInTheDocument();

    // Click to expand
    fireEvent.click(showDetailsButton);
    expect(
      screen.getByText('error.label: Detailed error message'),
    ).toBeInTheDocument();
  });
});
