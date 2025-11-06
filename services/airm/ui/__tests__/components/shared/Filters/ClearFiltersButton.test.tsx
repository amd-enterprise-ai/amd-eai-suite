// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render, screen } from '@testing-library/react';

import ClearFiltersButton from '@/components/shared/Filters/ClearFiltersButton';

describe('ClearFiltersButton', () => {
  const mockOnPress = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders correctly with required props', () => {
    render(<ClearFiltersButton isDisabled={false} onPress={mockOnPress} />);

    const button = screen.getByTestId('clear-filters-button');
    expect(button).toBeInTheDocument();
  });

  it('calls onPress when clicked and not disabled', () => {
    render(<ClearFiltersButton isDisabled={false} onPress={mockOnPress} />);

    const button = screen.getByTestId('clear-filters-button');
    fireEvent.click(button);

    expect(mockOnPress).toHaveBeenCalledTimes(1);
  });

  it('does not call onPress when clicked and disabled', () => {
    render(<ClearFiltersButton isDisabled={true} onPress={mockOnPress} />);

    const button = screen.getByTestId('clear-filters-button');
    fireEvent.click(button);

    expect(mockOnPress).not.toHaveBeenCalled();
  });

  it('is disabled when isDisabled prop is true', () => {
    render(<ClearFiltersButton isDisabled={true} onPress={mockOnPress} />);

    const button = screen.getByTestId('clear-filters-button');
    expect(button).toBeDisabled();
  });

  it('is enabled when isDisabled prop is false', () => {
    render(<ClearFiltersButton isDisabled={false} onPress={mockOnPress} />);

    const button = screen.getByTestId('clear-filters-button');
    expect(button).not.toBeDisabled();
  });

  it('maintains disabled state correctly', () => {
    const { rerender } = render(
      <ClearFiltersButton isDisabled={true} onPress={mockOnPress} />,
    );

    const button = screen.getByTestId('clear-filters-button');
    expect(button).toBeDisabled();

    // Click while disabled
    fireEvent.click(button);
    expect(mockOnPress).not.toHaveBeenCalled();

    // Re-render with enabled state
    rerender(<ClearFiltersButton isDisabled={false} onPress={mockOnPress} />);
    expect(button).not.toBeDisabled();

    // Click while enabled
    fireEvent.click(button);
    expect(mockOnPress).toHaveBeenCalledTimes(1);
  });
});
