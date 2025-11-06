// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';
import React from 'react';
import { vi } from 'vitest';

import StatusHeaderDisplay from '@/components/shared/ChipsAndStatus/StatusHeaderDisplay';

// Mock the HeroUI components
vi.mock('@heroui/react', () => ({
  Chip: ({ children, color, size }: any) => (
    <div data-testid="mock-chip" data-color={color} data-size={size}>
      {children}
    </div>
  ),
  Spinner: ({ size, color, className }: any) => (
    <div
      data-testid="mock-spinner"
      data-size={size}
      data-color={color}
      className={className}
    />
  ),
}));

// Mock icon component
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

describe('StatusHeaderDisplay', () => {
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
    failed: {
      label: 'Failed',
      color: 'danger' as const,
      icon: MockIcon,
    },
    default: {
      label: 'Default',
      icon: MockIcon,
    },
  };

  it('renders status header with icon component and success background', () => {
    render(<StatusHeaderDisplay variants={variants} type="active" />);

    const container = screen.getByText('Active');
    expect(container).toBeInTheDocument();
    expect(screen.getByTestId('mock-status-icon')).toBeInTheDocument();

    // Check that the wrapper div has the correct background classes
    const wrapper = container.closest('div');
    expect(wrapper).toHaveClass('dark:bg-success-800', 'bg-success-100');
  });

  it('renders status header with spinner and primary background', () => {
    render(<StatusHeaderDisplay variants={variants} type="processing" />);

    const container = screen.getByText('Processing');
    expect(container).toBeInTheDocument();
    expect(screen.getByTestId('mock-spinner')).toBeInTheDocument();
    expect(screen.getByTestId('mock-spinner')).toHaveAttribute(
      'data-color',
      'primary',
    );

    // Check that the wrapper div has the correct background classes
    const wrapper = container.closest('div');
    expect(wrapper).toHaveClass('dark:bg-primary-800', 'bg-primary-100');
  });

  it('renders status header with danger background', () => {
    render(<StatusHeaderDisplay variants={variants} type="failed" />);

    const container = screen.getByText('Failed');
    expect(container).toBeInTheDocument();

    // Check that the wrapper div has the correct background classes
    const wrapper = container.closest('div');
    expect(wrapper).toHaveClass('dark:bg-danger-800', 'bg-danger-100');
  });

  it('renders status header with default background for unknown color', () => {
    render(<StatusHeaderDisplay variants={variants} type="default" />);

    const container = screen.getByText('Default');
    expect(container).toBeInTheDocument();

    // Check that the wrapper div has the correct default background classes
    const wrapper = container.closest('div');
    expect(wrapper).toHaveClass('dark:bg-default-800', 'bg-default-100');
  });

  it('renders fallback when variant does not exist', () => {
    render(<StatusHeaderDisplay variants={variants} type="nonexistent" />);

    const container = screen.getByText('nonexistent!');
    expect(container).toBeInTheDocument();

    // Check that the wrapper div has the correct fallback background classes
    const wrapper = container.closest('div');
    expect(wrapper).toHaveClass('dark:bg-danger-800', 'bg-danger-100');
  });

  it('applies correct styling classes', () => {
    render(<StatusHeaderDisplay variants={variants} type="active" />);

    const wrapper = screen.getByText('Active').closest('div');
    expect(wrapper).toHaveClass('px-3', 'py-1', 'rounded-lg');
  });
});
