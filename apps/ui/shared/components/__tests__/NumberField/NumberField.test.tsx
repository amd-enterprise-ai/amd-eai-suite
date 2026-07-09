// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import React from 'react';
import { render, screen } from '@testing-library/react';
import { NumberField, NumberInput } from '@amdenterpriseai/components';
describe('NumberField adapter', () => {
  it('exposes NumberField and NumberInput as the same component', () => {
    expect(NumberField).toBe(NumberInput);
  });
  it('renders NumberField', () => {
    render(
      <NumberField
        aria-label="Replicas"
        data-testid="number-field"
        defaultValue={2}
        step={1}
      />,
    );
    expect(screen.getByTestId('number-field')).toBeInTheDocument();
  });
  it('renders NumberInput alias', () => {
    render(
      <NumberInput
        aria-label="Replicas"
        data-testid="number-input"
        defaultValue={1}
        step={1}
      />,
    );
    expect(screen.getByTestId('number-input')).toBeInTheDocument();
  });
});
