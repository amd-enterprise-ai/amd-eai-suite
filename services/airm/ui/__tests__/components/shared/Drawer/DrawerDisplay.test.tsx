// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, render, screen } from '@testing-library/react';

import { DrawerDisplay } from '@/components/shared/Drawer';

import '@testing-library/jest-dom';

describe('DrawerDisplay', () => {
  it('renders the drawer with display elements', () => {
    act(() => {
      render(
        <DrawerDisplay isOpen={true} title="Add User">
          <span>Some display</span>
        </DrawerDisplay>,
      );
    });

    expect(screen.getByText('Add User')).toBeInTheDocument();
    expect(screen.getByText('Some display')).toBeInTheDocument();
  });
});
