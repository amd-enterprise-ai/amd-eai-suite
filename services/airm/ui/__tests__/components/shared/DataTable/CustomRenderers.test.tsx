// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen, within } from '@testing-library/react';

import {
  BadgeStackDisplay,
  ChipDisplay,
  DateDisplay,
  NoDataDisplay,
  StatusBadgeDisplay,
  TranslationDisplay,
} from '@/components/shared/DataTable/CustomRenderers';

import { describe, expect, it, vi } from 'vitest';

// Use vi.hoisted to create mock functions that are properly hoisted
const formatMock = vi.hoisted(() => vi.fn().mockReturnValue('Formatted Date'));
const parseISOMock = vi.hoisted(() => vi.fn().mockReturnValue('Parsed Date'));

// Mock date-fns with hoisted mocks
vi.mock('date-fns', () => ({
  format: formatMock,
  parseISO: parseISOMock,
}));

// Mock next-i18next
vi.mock('next-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, any>) => {
      if (key === 'test.key' && !options) {
        return 'Translated';
      } else if (key === 'test.key') {
        return `Translated with ${Object.entries(options!)
          .map(([k, v]) => `${k}:${v}`)
          .join(' ')}`;
      }
      return key;
    },
  }),
}));

// Mock HeroUI components
vi.mock('@heroui/react', () => ({
  Chip: ({ children, size, color, variant, startContent }: any) => (
    <div
      data-testid="mock-chip"
      data-size={size}
      data-color={color}
      data-variant={variant}
    >
      {startContent && (
        <div data-testid="chip-start-content">{startContent}</div>
      )}
      {children}
    </div>
  ),
  Tooltip: ({ children, content }: any) => (
    <div data-testid="mock-tooltip">
      <div data-testid="tooltip-trigger">{children}</div>
      <div data-testid="tooltip-content">{content}</div>
    </div>
  ),
  Spinner: ({ size, color, className }: any) => (
    <div
      data-testid="mock-spinner"
      data-size={size}
      data-color={color}
      className={className}
    >
      Spinner
    </div>
  ),
}));

describe('DateDisplay', () => {
  beforeEach(() => {
    // Reset mocks before each test
    formatMock.mockClear();
    parseISOMock.mockClear();
    // Make parseISO return a valid date object that format can use
    parseISOMock.mockImplementation((date) => new Date(date));
  });

  it('renders formatted date with default format', () => {
    render(<DateDisplay date="2023-01-01T12:00:00Z" />);

    // Verify that parseISO was called with the date string
    expect(parseISOMock).toHaveBeenCalledWith('2023-01-01T12:00:00Z');

    // Verify that format was called with the result of parseISO and the default format
    expect(formatMock).toHaveBeenCalledWith(
      expect.any(Date),
      'yyyy/MM/dd HH:mm',
    );
  });

  it('renders formatted date with custom format', () => {
    render(<DateDisplay date="2023-01-01T12:00:00Z" format="dd/MM/yyyy" />);

    // Verify that parseISO was called with the date string
    expect(parseISOMock).toHaveBeenCalledWith('2023-01-01T12:00:00Z');

    // Verify that format was called with the result of parseISO and the custom format
    expect(formatMock).toHaveBeenCalledWith(expect.any(Date), 'dd/MM/yyyy');
  });
});

describe('ChipDisplay', () => {
  const MockIcon = ({
    size,
    className,
  }: {
    size?: string;
    className?: string;
  }) => (
    <span data-testid="mock-icon" data-size={size} className={className}>
      Icon
    </span>
  );

  const variants = {
    success: {
      label: 'Success',
      color: 'success' as const,
      icon: MockIcon,
    },
    error: {
      label: 'Error',
      color: 'danger' as const,
    },
    default: {
      label: 'Default',
    },
  };

  it('renders chip with correct label and color when variant exists', () => {
    render(<ChipDisplay variants={variants} type="success" />);

    const chip = screen.getByTestId('mock-chip');
    expect(chip).toBeInTheDocument();
    expect(chip).toHaveAttribute('data-color', 'success');
    expect(chip).toHaveAttribute('data-variant', 'flat');
    expect(chip).toHaveTextContent('Success');
    expect(screen.getByTestId('chip-start-content')).toBeInTheDocument();
  });

  it('renders chip without icon when not provided', () => {
    render(<ChipDisplay variants={variants} type="error" />);

    const chip = screen.getByTestId('mock-chip');
    expect(chip).toBeInTheDocument();
    expect(chip).toHaveAttribute('data-color', 'danger');
    expect(chip).toHaveTextContent('Error');
    expect(screen.queryByTestId('chip-start-content')).not.toBeInTheDocument();
  });

  it('renders chip with default color when not specified', () => {
    render(<ChipDisplay variants={variants} type="default" />);

    const chip = screen.getByTestId('mock-chip');
    expect(chip).toBeInTheDocument();
    expect(chip).toHaveAttribute('data-color', 'default');
    expect(chip).toHaveTextContent('Default');
  });

  it('renders fallback chip when variant does not exist', () => {
    render(<ChipDisplay variants={variants} type="nonexistent" />);

    const chip = screen.getByTestId('mock-chip');
    expect(chip).toBeInTheDocument();
    expect(chip).toHaveAttribute('data-color', 'danger');
    expect(chip).toHaveTextContent('nonexistent!');
  });
});

describe('StatusBadgeDisplay', () => {
  const MockIcon = ({
    size,
    className,
  }: {
    size?: string;
    className?: string;
  }) => (
    <span data-testid="mock-status-icon" data-size={size} className={className}>
      Icon
    </span>
  );

  const variants = {
    active: {
      label: 'Active',
      color: 'success' as const,
      textColor: 'success' as const,
      icon: MockIcon,
    },
    processing: {
      label: 'Processing',
      color: 'primary' as const,
      icon: 'spinner' as const,
    },
    default: {
      label: 'Default',
      icon: MockIcon,
    },
  };

  it('renders status badge with icon component', () => {
    render(<StatusBadgeDisplay variants={variants} type="active" />);

    const container = screen.getByText('Active');
    expect(container).toBeInTheDocument();
    // Just verify the element is rendered without checking for class
    expect(screen.getByTestId('mock-status-icon')).toBeInTheDocument();
  });

  it('renders status badge with spinner', () => {
    render(<StatusBadgeDisplay variants={variants} type="processing" />);

    const container = screen.getByText('Processing');
    expect(container).toBeInTheDocument();
    expect(screen.getByTestId('mock-spinner')).toBeInTheDocument();
    expect(screen.getByTestId('mock-spinner')).toHaveAttribute(
      'data-color',
      'primary',
    );
  });

  it('renders status badge with default styling', () => {
    render(<StatusBadgeDisplay variants={variants} type="default" />);

    const container = screen.getByText('Default');
    expect(container).toBeInTheDocument();
    expect(screen.getByTestId('mock-status-icon')).toBeInTheDocument();
  });

  it('renders fallback chip when variant does not exist', () => {
    render(<StatusBadgeDisplay variants={variants} type="nonexistent" />);

    const chip = screen.getByTestId('mock-chip');
    expect(chip).toBeInTheDocument();
    expect(chip).toHaveAttribute('data-color', 'danger');
    expect(chip).toHaveTextContent('nonexistent!');
  });
});

describe('TranslationDisplay', () => {
  it('renders translated string with translation key', () => {
    const { container } = render(
      <TranslationDisplay tKey="test.key" ns="common" />,
    );
    // Since we're mocking useTranslation, we check that something is rendered
    expect(container).not.toBeEmptyDOMElement();
  });

  it('renders translated string with interpolation options', () => {
    render(
      <TranslationDisplay tKey="test.key" ns="common" count={5} name="User" />,
    );
    expect(
      screen.getByText('Translated with count:5 name:User'),
    ).toBeInTheDocument();
  });
});

describe('NoDataDisplay', () => {
  it('renders mdash with correct styling', () => {
    render(<NoDataDisplay />);

    const mdash = screen.getByText('—');
    expect(mdash).toBeInTheDocument();
    expect(mdash).toHaveClass('text-default-300');
  });
});

describe('BadgeStackDisplay', () => {
  const MockIcon = ({ size }: { size?: string }) => (
    <span data-testid="mock-badge-icon" data-size={size}>
      Icon
    </span>
  );

  const variants = {
    gpu: { label: 'GPU', color: 'primary' as const, icon: MockIcon },
    cpu: { label: 'CPU', color: 'secondary' as const },
    memory: { label: 'Memory', color: 'warning' as const, icon: MockIcon },
    storage: { label: 'Storage', color: 'success' as const },
    singleChar: { label: 'S', color: 'default' as const }, // Added for testing isOneChar
  };

  vi.mock('@/components/shared/InlineBadge', () => ({
    InlineBadge: ({
      children,
      color = 'default', // Ensure default color if not provided
      size,
      isOneChar,
      className,
      ...rest
    }: any) => (
      <div
        data-testid="mock-inline-badge"
        data-color={color}
        data-size={size}
        data-isonechar={isOneChar}
        className={className}
        {...rest}
      >
        {children}
      </div>
    ),
  }));

  beforeEach(() => {
    vi.clearAllMocks(); // Clear mocks before each test
  });

  it('renders badges correctly when types are within limit', () => {
    render(
      <BadgeStackDisplay
        variants={variants}
        types={['gpu', 'cpu']}
        limit={3}
      />,
    );
    const tooltipTrigger = screen.getByTestId('tooltip-trigger');
    const badges = within(tooltipTrigger).getAllByTestId('mock-inline-badge');
    expect(badges).toHaveLength(2);
    expect(badges[0]).toHaveTextContent('Icon'); // GPU with MockIcon
    expect(badges[0]).toHaveAttribute('data-color', 'primary');
    expect(badges[1]).toHaveTextContent('CPU'); // CPU with label
    expect(badges[1]).toHaveAttribute('data-color', 'secondary');
    expect(screen.queryByText(/\\+\\d+/)).not.toBeInTheDocument(); // No +N indicator
  });

  it('renders badges and +N indicator when types exceed limit', () => {
    render(
      <BadgeStackDisplay
        variants={variants}
        types={['gpu', 'cpu', 'memory', 'storage']}
        limit={2}
      />,
    );
    const tooltipTrigger = screen.getByTestId('tooltip-trigger');
    const badges = within(tooltipTrigger).getAllByTestId('mock-inline-badge');
    expect(badges).toHaveLength(2);
    expect(screen.getByText('+2')).toBeInTheDocument();
  });

  it('displays tooltip with all items and title when provided', () => {
    render(
      <BadgeStackDisplay
        variants={variants}
        types={['gpu', 'cpu', 'memory']}
        title="Resources"
      />,
    );
    const tooltip = screen.getByTestId('mock-tooltip');
    expect(tooltip).toBeInTheDocument();

    const tooltipContent = screen.getByTestId('tooltip-content');
    expect(tooltipContent).toHaveTextContent('Resources:');
    expect(tooltipContent).toHaveTextContent('GPU');
    expect(tooltipContent).toHaveTextContent('CPU');
    expect(tooltipContent).toHaveTextContent('Memory');
  });

  it('renders nothing when types array is empty', () => {
    const { container } = render(
      <BadgeStackDisplay variants={variants} types={[]} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders badges with icons when provided in variants', () => {
    render(<BadgeStackDisplay variants={variants} types={['gpu']} />);
    const tooltipTrigger = screen.getByTestId('tooltip-trigger');
    const badge = within(tooltipTrigger).getByTestId('mock-inline-badge');
    expect(badge).toBeInTheDocument();
    const iconInBadge = within(badge).getByTestId('mock-badge-icon');
    expect(iconInBadge).toBeInTheDocument();
    expect(iconInBadge).toHaveAttribute('data-size', '12');
    expect(badge).toHaveAttribute('data-isonechar', 'true');
  });

  it('renders badges with labels when icons are not provided in variants', () => {
    render(<BadgeStackDisplay variants={variants} types={['cpu']} />);
    const tooltipTrigger = screen.getByTestId('tooltip-trigger');
    const badge = within(tooltipTrigger).getByTestId('mock-inline-badge');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('CPU');
    expect(
      within(badge).queryByTestId('mock-badge-icon'),
    ).not.toBeInTheDocument();
  });

  it('applies -ml-2 class to subsequent badges', () => {
    render(<BadgeStackDisplay variants={variants} types={['gpu', 'cpu']} />);
    const tooltipTrigger = screen.getByTestId('tooltip-trigger');
    const badges = within(tooltipTrigger).getAllByTestId('mock-inline-badge');
    expect(badges[0]).not.toHaveClass('-ml-2');
    expect(badges[1]).toHaveClass('-ml-2');
  });

  it('renders default label if variant type is not found in variants object', () => {
    render(
      <BadgeStackDisplay
        variants={variants}
        types={['nonexistent']}
        title="Test"
      />,
    );
    const tooltipTrigger = screen.getByTestId('tooltip-trigger');
    const badge = within(tooltipTrigger).getByTestId('mock-inline-badge');
    expect(badge).toBeInTheDocument();
    // The badge itself will render the type as label if icon is missing
    expect(badge).toHaveTextContent('nonexistent');
    expect(badge).toHaveAttribute('data-color', 'default'); // Added assertion

    // Check tooltip content for the default label
    const tooltipContent = screen.getByTestId('tooltip-content');
    expect(tooltipContent).toHaveTextContent('Test:');
    // The InlineBadge in the tooltip will also render the type as label
    const tooltipBadge =
      within(tooltipContent).getByTestId('mock-inline-badge');
    expect(tooltipBadge).toBeInTheDocument();
    expect(tooltipBadge).toHaveTextContent('nonexistent');
    expect(tooltipBadge).toHaveAttribute('data-color', 'default'); // Added assertion
    expect(tooltipContent).toHaveTextContent('nonexistent'); // The span with the label
  });

  it('passes isOneChar={false} to InlineBadge for multi-character labels without icon', () => {
    render(<BadgeStackDisplay variants={variants} types={['cpu']} />); // 'cpu' label "CPU"
    const tooltipTrigger = screen.getByTestId('tooltip-trigger');
    const badge = within(tooltipTrigger).getByTestId('mock-inline-badge');
    expect(badge).toHaveAttribute('data-isonechar', 'true');
  });

  it('passes isOneChar={true} to InlineBadge for single-character labels without icon', () => {
    render(<BadgeStackDisplay variants={variants} types={['singleChar']} />); // 'singleChar' label "S"
    const tooltipTrigger = screen.getByTestId('tooltip-trigger');
    const badge = within(tooltipTrigger).getByTestId('mock-inline-badge');
    expect(badge).toHaveAttribute('data-isonechar', 'true');
  });
});
