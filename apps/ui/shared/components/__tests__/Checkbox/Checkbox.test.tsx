// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { Checkbox } from '@amdenterpriseai/components';

describe('Checkbox adapter', () => {
  it('renders unselected by default', () => {
    render(<Checkbox data-testid="checkbox">Accept</Checkbox>);
    expect(screen.getByTestId('checkbox')).toBeInTheDocument();
    expect(screen.getByRole('checkbox')).not.toBeChecked();
  });
  it('renders selected when isSelected is true', () => {
    render(
      <Checkbox isSelected data-testid="checkbox">
        Checked
      </Checkbox>,
    );
    expect(screen.getByRole('checkbox')).toBeChecked();
  });
  it('calls onValueChange when toggled', () => {
    const onValueChange = vi.fn();
    render(
      <Checkbox isSelected={false} onValueChange={onValueChange}>
        Agree
      </Checkbox>,
    );
    fireEvent.click(screen.getByRole('checkbox'));
    expect(onValueChange).toHaveBeenCalledWith(true);
  });
  it('respects isDisabled', () => {
    render(
      <Checkbox isDisabled data-testid="checkbox">
        Disabled
      </Checkbox>,
    );
    expect(screen.getByRole('checkbox')).toBeDisabled();
  });
});
