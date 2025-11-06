// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render, screen } from '@testing-library/react';

import SliderInput from '@/components/shared/SliderInput/SliderInput';

describe('SliderInput', () => {
  const defaultProps = {
    id: 'test-slider',
    ariaLabel: 'Test Slider',
    min: 0,
    max: 100,
  };

  it('renders SliderInput component', () => {
    render(<SliderInput {...defaultProps} />);
    expect(screen.getByRole('slider')).toBeInTheDocument();
    expect(screen.getByRole('spinbutton')).toBeInTheDocument();
  });

  it('sets default value correctly', () => {
    render(<SliderInput {...defaultProps} defaultValue={50} />);
    expect(screen.getByRole('slider')).toHaveValue('50');
    expect(screen.getByRole('spinbutton')).toHaveValue(50);
  });

  it('handles slider change', () => {
    render(<SliderInput {...defaultProps} />);
    const slider = screen.getByRole('slider');
    fireEvent.change(slider, { target: { value: 30 } });
    expect(slider).toHaveValue('30');
    expect(screen.getByRole('spinbutton')).toHaveValue(30);
  });

  it('handles input change', () => {
    render(<SliderInput {...defaultProps} />);
    const input = screen.getByRole('spinbutton');
    fireEvent.change(input, { target: { value: 40 } });
    expect(input).toHaveValue(40);
    expect(screen.getByRole('slider')).toHaveValue('40');
  });

  it('bounds value within min and max', () => {
    render(<SliderInput {...defaultProps} />);
    const input = screen.getByRole('spinbutton');
    fireEvent.change(input, { target: { value: 150 } });
    expect(input).toHaveValue(100);
    expect(screen.getByRole('slider')).toHaveValue('100');

    fireEvent.change(input, { target: { value: -10 } });
    expect(input).toHaveValue(0);
    expect(screen.getByRole('slider')).toHaveValue('0');
  });

  it('updates value when prop changes', () => {
    const { rerender } = render(<SliderInput {...defaultProps} value={20} />);
    expect(screen.getByRole('slider')).toHaveValue('20');
    expect(screen.getByRole('spinbutton')).toHaveValue(20);

    rerender(<SliderInput {...defaultProps} value={80} />);
    expect(screen.getByRole('slider')).toHaveValue('80');
    expect(screen.getByRole('spinbutton')).toHaveValue(80);
  });
});
