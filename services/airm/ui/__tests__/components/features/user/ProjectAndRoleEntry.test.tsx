// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render, screen } from '@testing-library/react';

import { ProjectAndRoleEntry } from '@/components/features/user';

import '@testing-library/jest-dom';

describe('GroupAndRoleEntry', () => {
  const defaultProps = {
    name: 'Test Group',
    description: 'This is a test group',
  };

  it('renders the name and description', () => {
    render(<ProjectAndRoleEntry {...defaultProps} />);
    expect(screen.getByText('Test Group')).toBeInTheDocument();
    expect(screen.getByText('This is a test group')).toBeInTheDocument();
  });

  it('does not render the button when onPress is not provided', () => {
    render(<ProjectAndRoleEntry {...defaultProps} />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('calls onPress when the button is clicked', () => {
    const onPress = vi.fn();
    render(<ProjectAndRoleEntry {...defaultProps} onPress={onPress} />);
    const button = screen.getByRole('button');
    fireEvent.click(button);
    expect(onPress).toHaveBeenCalledTimes(1);
  });
});
