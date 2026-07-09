// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { Switch } from '@amdenterpriseai/components';

describe('Switch adapter', () => {
  it('renders unselected by default', () => {
    render(<Switch data-testid="switch">Label</Switch>);
    expect(screen.getByTestId('switch')).toBeInTheDocument();
    expect(screen.getByRole('switch')).not.toBeChecked();
  });
  it('renders selected when isSelected is true', () => {
    render(
      <Switch isSelected data-testid="switch">
        On
      </Switch>,
    );
    expect(screen.getByRole('switch')).toBeChecked();
  });
  it('calls onValueChange when toggled', () => {
    const onValueChange = vi.fn();
    render(
      <Switch isSelected={false} onValueChange={onValueChange}>
        Toggle
      </Switch>,
    );
    fireEvent.click(screen.getByRole('switch'));
    expect(onValueChange).toHaveBeenCalledWith(true);
  });
  it('respects isDisabled', () => {
    render(
      <Switch isDisabled data-testid="switch">
        Disabled
      </Switch>,
    );
    expect(screen.getByRole('switch')).toBeDisabled();
  });
});
