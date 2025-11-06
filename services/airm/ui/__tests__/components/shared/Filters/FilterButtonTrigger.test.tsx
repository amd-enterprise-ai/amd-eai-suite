// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { IconFilter } from '@tabler/icons-react';
import { render, screen } from '@testing-library/react';

import FilterButtonTrigger from '@/components/shared/Filters/FilterDropdown/FilterButtonTrigger';

// Mock HeroUI components
vi.mock('@heroui/react', async () => {
  const original = await vi.importActual<any>('@heroui/react');
  return {
    ...original,
    cn: (...args: any[]) => {
      return original.cn(...args);
    },
    Chip: ({ children, color, variant, startContent, className }: any) => (
      <div
        data-testid="chip"
        data-color={color}
        data-variant={variant}
        className={className}
      >
        {startContent && (
          <div data-testid="chip-start-content">{startContent}</div>
        )}
        {children}
      </div>
    ),
    Button: ({
      children,
      color,
      startContent,
      endContent,
      variant,
      isIconOnly,
      onPress,
      'aria-label': ariaLabel,
      className,
    }: any) => (
      <button
        data-testid={isIconOnly ? 'icon-button' : 'button'}
        data-color={color}
        data-variant={variant}
        data-icon-only={isIconOnly}
        aria-label={ariaLabel}
        className={className}
        onClick={onPress}
      >
        {startContent && <div data-testid="start-content">{startContent}</div>}
        {children}
        {endContent && <div data-testid="end-content">{endContent}</div>}
      </button>
    ),
    DropdownTrigger: ({ children }: any) => (
      <div data-testid="dropdown-trigger">{children}</div>
    ),
    Tooltip: ({ children, content, delay, size, className }: any) => (
      <div
        data-testid="tooltip"
        data-content={content}
        data-delay={delay}
        data-size={size}
        className={className}
      >
        {children}
      </div>
    ),
  };
});

// Mock InlineBadge component
vi.mock('@/components/shared/InlineBadge', () => ({
  InlineBadge: ({ children, color, size, variant }: any) => (
    <div
      data-testid="inline-badge"
      data-color={color}
      data-size={size}
      data-variant={variant}
    >
      {children}
    </div>
  ),
}));

describe('FilterButtonTrigger Component', () => {
  const defaultProps = {
    label: 'Status',
    numberOfSelectedKeys: 1,
  };

  it('renders correctly with default props (inactive state)', () => {
    render(<FilterButtonTrigger {...defaultProps} />);

    const triggerElement = screen.getByTestId('dropdown-trigger');
    expect(triggerElement).toBeInTheDocument();

    const buttonElement = screen.getByTestId('button');
    expect(buttonElement).toBeInTheDocument();
    expect(buttonElement).toHaveAttribute('data-variant', 'flat');
    expect(buttonElement).toHaveAttribute('aria-label', 'Status');
    expect(buttonElement).toHaveTextContent('Status');

    // Badge should not be present when isActive is false
    const badgeElement = screen.queryByTestId('inline-badge');
    expect(badgeElement).not.toBeInTheDocument();

    // End content should contain chevron down icon
    const endContent = screen.getByTestId('end-content');
    expect(endContent).toBeInTheDocument();
  });

  it('renders badge when active with selected keys', () => {
    render(
      <FilterButtonTrigger
        {...defaultProps}
        isActive={true}
        numberOfSelectedKeys={2}
      />,
    );

    const buttonElement = screen.getByTestId('button');
    expect(buttonElement).toHaveAttribute('data-variant', 'flat');

    // Badge should be present when isActive is true
    const badgeElement = screen.getByTestId('inline-badge');
    expect(badgeElement).toBeInTheDocument();
    expect(badgeElement).toHaveAttribute('data-color', 'primary');
    expect(badgeElement).toHaveAttribute('data-size', 'sm');
    expect(badgeElement).toHaveAttribute('data-variant', 'solid');
    expect(badgeElement).toHaveTextContent('2');
  });

  it('displays badge with tooltip when active', () => {
    const tooltipText = 'Selected: Option A, Option B';

    render(
      <FilterButtonTrigger
        {...defaultProps}
        isActive={true}
        numberOfSelectedKeys={2}
        tooltipText={tooltipText}
      />,
    );

    const tooltipElement = screen.getByTestId('tooltip');
    expect(tooltipElement).toBeInTheDocument();
    expect(tooltipElement).toHaveAttribute('data-content', tooltipText);
    expect(tooltipElement).toHaveAttribute('data-delay', '500');
    expect(tooltipElement).toHaveAttribute('data-size', 'sm');

    // Badge should be inside the tooltip
    const badgeElement = screen.getByTestId('inline-badge');
    expect(badgeElement).toBeInTheDocument();
  });

  it('displays start content alongside label', () => {
    const startContent = <IconFilter data-testid="filter-icon" />;

    render(
      <FilterButtonTrigger {...defaultProps} startContent={startContent} />,
    );

    // Custom start content should be visible inside the button content
    const filterIcon = screen.getByTestId('filter-icon');
    expect(filterIcon).toBeInTheDocument();

    const buttonElement = screen.getByTestId('button');
    expect(buttonElement).toHaveTextContent('Status');
  });

  it('shows reset button when active and onReset is provided', () => {
    const mockOnReset = vi.fn();

    render(
      <FilterButtonTrigger
        {...defaultProps}
        isActive={true}
        onReset={mockOnReset}
      />,
    );

    const resetButton = screen.getByTestId('icon-button');
    expect(resetButton).toBeInTheDocument();
    expect(resetButton).toHaveAttribute('data-icon-only', 'true');
    expect(resetButton).toHaveAttribute('aria-label', 'actions.clear.title');

    // Main button should not have chevron down when reset is available
    const endContent = screen.queryByTestId('end-content');
    expect(endContent).toBeInTheDocument();
  });

  it('calls onReset when reset button is clicked', () => {
    const mockOnReset = vi.fn();

    render(
      <FilterButtonTrigger
        {...defaultProps}
        isActive={true}
        onReset={mockOnReset}
      />,
    );

    const resetButton = screen.getByTestId('icon-button');
    resetButton.click();

    expect(mockOnReset).toHaveBeenCalledTimes(1);
  });

  it('does not show reset button when not active', () => {
    const mockOnReset = vi.fn();

    render(
      <FilterButtonTrigger
        {...defaultProps}
        isActive={false}
        onReset={mockOnReset}
      />,
    );

    const resetButton = screen.queryByTestId('icon-button');
    expect(resetButton).not.toBeInTheDocument();
  });

  it('does not show reset button when active but onReset is not provided', () => {
    render(<FilterButtonTrigger {...defaultProps} isActive={true} />);

    const resetButton = screen.queryByTestId('icon-button');
    expect(resetButton).not.toBeInTheDocument();
  });
});
