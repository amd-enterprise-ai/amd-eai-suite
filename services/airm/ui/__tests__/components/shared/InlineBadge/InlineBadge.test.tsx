// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';
import React from 'react';

import {
  InlineBadge,
  InlineBadgeProps,
} from '@/components/shared/InlineBadge/InlineBadge';

describe('InlineBadge', () => {
  const defaultProps: InlineBadgeProps = {
    children: 'Test Badge',
  };

  const renderComponent = (props: InlineBadgeProps = defaultProps) => {
    return render(<InlineBadge {...props} />);
  };

  it('should render the badge with children', () => {
    renderComponent();
    expect(screen.getByText('Test Badge')).toBeInTheDocument();
  });

  it('should render with default props when no props are provided', () => {
    render(<InlineBadge {...({} as InlineBadgeProps)} />);
    expect(screen.queryByText(/.+/)).not.toBeInTheDocument();
  });

  it('should display only the first character when isOneChar is true', () => {
    renderComponent({ ...defaultProps, children: 'Test', isOneChar: true });
    expect(screen.getByText('T')).toBeInTheDocument();
    expect(screen.queryByText('Test')).not.toBeInTheDocument();
  });

  it('should convert the first character to uppercase when isOneChar is true', () => {
    renderComponent({ ...defaultProps, children: 'test', isOneChar: true });
    expect(screen.getByText('T')).toBeInTheDocument();
  });

  it('should be invisible when isInvisible is true', () => {
    const { container } = renderComponent({
      ...defaultProps,
      isInvisible: true,
    });
    expect(container.firstChild).toHaveAttribute('data-invisible', 'true');
  });

  it('should apply custom className', () => {
    const { container } = renderComponent({
      ...defaultProps,
      className: 'custom-class',
    });
    expect(container.firstChild).toHaveClass('custom-class');
  });

  (['sm', 'md', 'lg'] as const).forEach((size) => {
    it(`should render with size ${size}`, () => {
      renderComponent({ ...defaultProps, size });
      expect(screen.getByText('Test Badge')).toBeInTheDocument();
    });
  });

  (
    ['default', 'primary', 'secondary', 'success', 'warning', 'danger'] as const
  ).forEach((color) => {
    it(`should render with color ${color}`, () => {
      renderComponent({ ...defaultProps, color });
      expect(screen.getByText('Test Badge')).toBeInTheDocument();
    });
  });

  it('should render non-string children', () => {
    const childElement = <span data-testid="child-element">Hello</span>;
    renderComponent({ children: childElement });
    expect(screen.getByTestId('child-element')).toBeInTheDocument();
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });

  it('should not apply animation class when disableAnimation is true', () => {
    const { container } = renderComponent({
      ...defaultProps,
      disableAnimation: true,
    });

    expect(container.firstChild).not.toHaveClass(
      'transition-transform-opacity',
    );
  });

  it('should apply animation class when disableAnimation is false (default)', () => {
    const { container } = renderComponent({
      ...defaultProps,
      disableAnimation: false,
    });
    expect(container.firstChild).toHaveClass('transition-transform-opacity');
  });

  it('should show outline by default', () => {
    const { container } = renderComponent();

    expect(container.firstChild).toHaveClass('border-2');
    expect(container.firstChild).toHaveClass('border-background');
  });

  it('should not show outline when showOutline is false', () => {
    const { container } = renderComponent({
      ...defaultProps,
      showOutline: false,
    });

    expect(container.firstChild).toHaveClass('border-0');
    expect(container.firstChild).toHaveClass('border-transparent');
  });
});
