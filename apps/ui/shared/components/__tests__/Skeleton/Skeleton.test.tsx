// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';
import { render, screen } from '@testing-library/react';
import { Skeleton } from '@amdenterpriseai/components';

describe('Skeleton adapter', () => {
  it('renders with className', () => {
    render(<Skeleton className="h-4 w-24 rounded-lg" data-testid="skeleton" />);
    expect(screen.getByTestId('skeleton')).toHaveClass(
      'h-4',
      'w-24',
      'rounded-lg',
    );
  });
  it('renders children when provided', () => {
    render(<Skeleton data-testid="skeleton">Loading</Skeleton>);
    expect(screen.getByTestId('skeleton')).toBeInTheDocument();
  });
  it('respects isLoaded', () => {
    render(
      <Skeleton isLoaded data-testid="skeleton">
        Content
      </Skeleton>,
    );
    expect(screen.getByText('Content')).toBeInTheDocument();
  });
});
