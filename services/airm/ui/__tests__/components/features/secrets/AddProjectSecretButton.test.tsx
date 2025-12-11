// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AddProjectSecretButton from '@/components/features/secrets/AddProjectSecretButton';

describe('AddProjectSecretButton', () => {
  const mockOnOpenProjectSecret = vi.fn();
  const mockOnOpenProjectAssignment = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the button with correct label', () => {
    render(
      <AddProjectSecretButton
        onOpenProjectSecret={mockOnOpenProjectSecret}
        onOpenProjectAssignment={mockOnOpenProjectAssignment}
      />,
    );

    expect(
      screen.getByText('actions.addProjectSecret.label'),
    ).toBeInTheDocument();
  });

  it('renders disabled when disabled prop is true', () => {
    render(
      <AddProjectSecretButton
        disabled
        onOpenProjectSecret={mockOnOpenProjectSecret}
        onOpenProjectAssignment={mockOnOpenProjectAssignment}
      />,
    );

    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });

  it('opens dropdown and shows menu items when clicked', async () => {
    const user = userEvent.setup();
    render(
      <AddProjectSecretButton
        onOpenProjectSecret={mockOnOpenProjectSecret}
        onOpenProjectAssignment={mockOnOpenProjectAssignment}
      />,
    );

    const button = screen.getByRole('button');
    await user.click(button);

    expect(
      screen.getByText('actions.addProjectSecret.options.add.label'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('actions.addProjectSecret.options.assign.label'),
    ).toBeInTheDocument();
  });

  it('calls onOpenProjectSecret when add option is clicked', async () => {
    const user = userEvent.setup();
    render(
      <AddProjectSecretButton
        onOpenProjectSecret={mockOnOpenProjectSecret}
        onOpenProjectAssignment={mockOnOpenProjectAssignment}
      />,
    );

    const button = screen.getByRole('button');
    await user.click(button);

    const addOption = screen.getByText(
      'actions.addProjectSecret.options.add.label',
    );
    await user.click(addOption);

    expect(mockOnOpenProjectSecret).toHaveBeenCalledTimes(1);
  });

  it('calls onOpenProjectAssignment when assign option is clicked', async () => {
    const user = userEvent.setup();
    render(
      <AddProjectSecretButton
        onOpenProjectSecret={mockOnOpenProjectSecret}
        onOpenProjectAssignment={mockOnOpenProjectAssignment}
      />,
    );

    const button = screen.getByRole('button');
    await user.click(button);

    const assignOption = screen.getByText(
      'actions.addProjectSecret.options.assign.label',
    );
    await user.click(assignOption);

    expect(mockOnOpenProjectAssignment).toHaveBeenCalledTimes(1);
  });

  it('has correct aria-label attribute', () => {
    render(
      <AddProjectSecretButton
        onOpenProjectSecret={mockOnOpenProjectSecret}
        onOpenProjectAssignment={mockOnOpenProjectAssignment}
      />,
    );

    const button = screen.getByRole('button');
    expect(button).toHaveAttribute(
      'aria-label',
      'actions.addProjectSecret.label',
    );
  });
});
