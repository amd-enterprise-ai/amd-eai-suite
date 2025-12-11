// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { fireEvent, render, screen } from '@testing-library/react';
import React, { act } from 'react';

import { AssignStorageButton } from '@/components/features/storages';

import wrapper from '@/__tests__/ProviderWrapper';

describe('AssignStorageButton', () => {
  it('renders the button with correct label', () => {
    const onAssignS3Storage = vi.fn();

    act(() => {
      render(<AssignStorageButton onAssignS3Storage={onAssignS3Storage} />, {
        wrapper,
      });
    });

    expect(
      screen.getByRole('button', { name: 'actions.assignStorage.label' }),
    ).toBeInTheDocument();
  });

  it('shows S3 option in dropdown when clicked', () => {
    const onAssignS3Storage = vi.fn();

    act(() => {
      render(<AssignStorageButton onAssignS3Storage={onAssignS3Storage} />, {
        wrapper,
      });
    });

    const button = screen.getByRole('button', {
      name: 'actions.assignStorage.label',
    });
    fireEvent.click(button);

    expect(
      screen.getByRole('menuitem', {
        name: 'actions.assignStorage.options.S3.label',
      }),
    ).toBeInTheDocument();
  });

  it('calls onAssignS3Storage when S3 option is clicked', () => {
    const onAssignS3Storage = vi.fn();

    act(() => {
      render(<AssignStorageButton onAssignS3Storage={onAssignS3Storage} />, {
        wrapper,
      });
    });

    const button = screen.getByRole('button', {
      name: 'actions.assignStorage.label',
    });
    fireEvent.click(button);

    const s3Option = screen.getByRole('menuitem', {
      name: 'actions.assignStorage.options.S3.label',
    });
    fireEvent.click(s3Option);

    expect(onAssignS3Storage).toHaveBeenCalledTimes(1);
  });

  it('disables the button when disabled prop is true', () => {
    const onAssignS3Storage = vi.fn();

    act(() => {
      render(
        <AssignStorageButton
          onAssignS3Storage={onAssignS3Storage}
          disabled={true}
        />,
        { wrapper },
      );
    });

    const button = screen.getByRole('button', {
      name: 'actions.assignStorage.label',
    });
    expect(button).toBeDisabled();
  });

  it('does not open dropdown when button is disabled', () => {
    const onAssignS3Storage = vi.fn();

    act(() => {
      render(
        <AssignStorageButton
          onAssignS3Storage={onAssignS3Storage}
          disabled={true}
        />,
        { wrapper },
      );
    });

    const button = screen.getByRole('button', {
      name: 'actions.assignStorage.label',
    });
    fireEvent.click(button);

    // Menu item should not appear
    expect(
      screen.queryByRole('menuitem', {
        name: 'actions.assignStorage.options.S3.label',
      }),
    ).not.toBeInTheDocument();
  });

  it('does not call handler when dropdown is disabled', () => {
    const onAssignS3Storage = vi.fn();

    act(() => {
      render(
        <AssignStorageButton
          onAssignS3Storage={onAssignS3Storage}
          disabled={true}
        />,
        { wrapper },
      );
    });

    const button = screen.getByRole('button', {
      name: 'actions.assignStorage.label',
    });
    fireEvent.click(button);

    expect(onAssignS3Storage).not.toHaveBeenCalled();
  });
});
