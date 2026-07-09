// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { render, screen } from '@testing-library/react';

import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@amdenterpriseai/components';

import '@testing-library/jest-dom';

describe('Popover adapter', () => {
  it('exposes compound sub-components', () => {
    expect(Popover.Trigger).toBe(PopoverTrigger);
    expect(Popover.Content).toBe(PopoverContent);
  });

  it('renders with compound component API', () => {
    render(
      <Popover>
        <Popover.Trigger>
          <button type="button">Open</button>
        </Popover.Trigger>
        <Popover.Content>
          <div>Popover body</div>
        </Popover.Content>
      </Popover>,
    );

    expect(screen.getByRole('button', { name: 'Open' })).toBeInTheDocument();
  });

  it('renders with flat alias API', () => {
    render(
      <Popover>
        <PopoverTrigger>
          <button type="button">Flat trigger</button>
        </PopoverTrigger>
        <PopoverContent>
          <div>Flat content</div>
        </PopoverContent>
      </Popover>,
    );

    expect(
      screen.getByRole('button', { name: 'Flat trigger' }),
    ).toBeInTheDocument();
  });
});
