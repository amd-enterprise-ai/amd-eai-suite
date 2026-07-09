// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React, { useState } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { Slider } from '@amdenterpriseai/components';

describe('Slider adapter', () => {
  it('renders with a numeric value', () => {
    render(
      <Slider
        aria-label="Test slider"
        value={0.5}
        minValue={0}
        maxValue={1}
        data-testid="slider"
      />,
    );
    expect(screen.getByTestId('slider')).toBeInTheDocument();
    expect(screen.getByRole('slider')).toBeInTheDocument();
  });

  it('calls onChange for single-value sliders', () => {
    const handleChange = vi.fn();
    render(
      <Slider
        aria-label="Test slider"
        value={0.25}
        minValue={0}
        maxValue={1}
        step={0.05}
        onChange={handleChange}
        data-testid="slider"
      />,
    );
    fireEvent.change(screen.getByRole('slider'), { target: { value: '0.5' } });
    expect(handleChange).toHaveBeenCalled();
  });

  it('respects step prop', () => {
    render(
      <Slider
        aria-label="Step slider"
        value={10}
        minValue={0}
        maxValue={100}
        step={5}
        data-testid="slider"
      />,
    );
    expect(screen.getByRole('slider')).toHaveAttribute('step', '5');
  });

  it('supports range values as a number array', () => {
    const RangeSlider = () => {
      const [value, setValue] = useState<[number, number]>([20, 80]);
      return (
        <Slider
          aria-label="Range slider"
          value={value}
          minValue={0}
          maxValue={100}
          onChange={(next) => {
            if (Array.isArray(next)) {
              setValue(next as [number, number]);
            }
          }}
          data-testid="range-slider"
        />
      );
    };
    render(<RangeSlider />);
    expect(screen.getByTestId('range-slider')).toBeInTheDocument();
    expect(screen.getAllByRole('slider')).toHaveLength(2);
  });

  it('passes isDisabled', () => {
    render(
      <Slider
        aria-label="Disabled slider"
        value={50}
        minValue={0}
        maxValue={100}
        isDisabled
        data-testid="slider"
      />,
    );
    expect(screen.getByRole('slider')).toBeDisabled();
  });
});
