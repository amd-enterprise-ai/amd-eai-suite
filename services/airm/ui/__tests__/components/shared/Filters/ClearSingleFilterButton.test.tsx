// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import ClearSingleFilterButton from '@/components/shared/Filters/ClearSingleFilterButton';

describe('ClearSingleFilterButton', () => {
  it('should render the button', () => {
    render(<ClearSingleFilterButton onPress={() => {}} />);
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('should call onPress when clicked', () => {
    const onPress = vi.fn();
    render(<ClearSingleFilterButton onPress={onPress} />);
    const button = screen.getByRole('button');
    fireEvent.click(button);
    expect(onPress).toHaveBeenCalledTimes(1);
  });
});
