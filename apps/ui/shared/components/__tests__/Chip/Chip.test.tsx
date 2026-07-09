// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';
import { render, screen } from '@testing-library/react';
import { Chip } from '@amdenterpriseai/components';

describe('Chip adapter', () => {
  it('renders children', () => {
    render(<Chip data-testid="chip">Label</Chip>);
    expect(screen.getByTestId('chip')).toBeInTheDocument();
    expect(screen.getByText('Label')).toBeInTheDocument();
  });

  it('renders with color and variant props', () => {
    render(
      <Chip color="success" variant="flat" data-testid="chip">
        Success
      </Chip>,
    );
    expect(screen.getByTestId('chip')).toBeInTheDocument();
    expect(screen.getByText('Success')).toBeInTheDocument();
  });

  it('renders with size prop', () => {
    render(
      <Chip size="sm" data-testid="chip">
        Small
      </Chip>,
    );
    expect(screen.getByTestId('chip')).toBeInTheDocument();
    expect(screen.getByText('Small')).toBeInTheDocument();
  });
});
