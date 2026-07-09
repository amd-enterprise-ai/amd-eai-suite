// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';

import { PageLoader } from '@/components/shared/PageLoader';

vi.mock('@amdenterpriseai/components', async (importOriginal) => {
  const actual =
    await importOriginal<typeof import('@amdenterpriseai/components')>();
  return {
    ...actual,
    Spinner: ({ size, color, ...props }: any) => (
      <div data-testid="spinner" data-size={size} data-color={color} {...props}>
        Loading spinner
      </div>
    ),
  };
});

describe('PageLoader', () => {
  it('renders a large primary spinner', () => {
    render(<PageLoader />);

    const spinner = screen.getByTestId('spinner');
    expect(spinner).toBeInTheDocument();
    expect(spinner).toHaveAttribute('data-size', 'lg');
    expect(spinner).toHaveAttribute('data-color', 'primary');
  });

  it('renders label when provided', () => {
    render(<PageLoader label="Loading models…" />);

    expect(screen.getByText('Loading models…')).toBeInTheDocument();
  });

  it('renders no label when omitted', () => {
    const { container } = render(<PageLoader />);

    expect(container.querySelector('p')).not.toBeInTheDocument();
  });

  it('applies testId to the container', () => {
    render(<PageLoader testId="my-loader" />);

    expect(screen.getByTestId('my-loader')).toBeInTheDocument();
  });

  it('merges className onto the container', () => {
    render(<PageLoader label="Loading…" className="h-full w-full" />);

    const container = screen.getByText('Loading…').closest('div');
    expect(container).toHaveClass('h-full', 'w-full', 'flex');
  });

  it('applies label text styling', () => {
    render(<PageLoader label="Loading…" />);

    expect(screen.getByText('Loading…')).toHaveClass(
      'text-center',
      'text-default-500',
      'text-sm',
    );
  });
});
