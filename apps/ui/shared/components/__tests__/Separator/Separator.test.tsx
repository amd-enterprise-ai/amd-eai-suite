// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import React from 'react';
import { render, screen } from '@testing-library/react';
import { Divider, Separator } from '@amdenterpriseai/components';
describe('Separator adapter', () => {
  it('exposes Separator and Divider as the same component', () => {
    expect(Separator).toBe(Divider);
  });
  it('renders Separator', () => {
    render(<Separator data-testid="separator" />);
    expect(screen.getByTestId('separator')).toBeInTheDocument();
  });
  it('renders vertical Divider', () => {
    render(<Divider data-testid="divider" orientation="vertical" />);
    expect(screen.getByTestId('divider')).toHaveAttribute(
      'aria-orientation',
      'vertical',
    );
  });
});
