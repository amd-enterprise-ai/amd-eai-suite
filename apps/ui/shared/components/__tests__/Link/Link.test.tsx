// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';
import { render, screen } from '@testing-library/react';
import { Link } from '@amdenterpriseai/components';

describe('Link adapter', () => {
  it('renders children', () => {
    render(
      <Link href="/test" data-testid="link">
        Label
      </Link>,
    );
    expect(screen.getByTestId('link')).toBeInTheDocument();
    expect(screen.getByText('Label')).toBeInTheDocument();
  });

  it('renders with href', () => {
    render(
      <Link href="/path" data-testid="link">
        Go
      </Link>,
    );
    expect(screen.getByTestId('link')).toHaveAttribute('href', '/path');
  });

  it('renders with color prop', () => {
    render(
      <Link href="#" color="primary" data-testid="link">
        Primary
      </Link>,
    );
    expect(screen.getByTestId('link')).toBeInTheDocument();
    expect(screen.getByText('Primary')).toBeInTheDocument();
  });
});
