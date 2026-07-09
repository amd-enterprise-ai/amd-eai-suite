// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';
import { render, screen } from '@testing-library/react';
import { Tooltip } from '@amdenterpriseai/components';

describe('Tooltip adapter', () => {
  it('renders trigger content', () => {
    render(
      <Tooltip content="Help text">
        <button type="button">Trigger</button>
      </Tooltip>,
    );
    expect(screen.getByRole('button', { name: 'Trigger' })).toBeInTheDocument();
  });
});
