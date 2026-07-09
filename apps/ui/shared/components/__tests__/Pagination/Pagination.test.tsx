// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { Pagination } from '@amdenterpriseai/components';

describe('Pagination adapter', () => {
  it('renders page controls for the given total', () => {
    render(
      <Pagination
        showControls
        page={1}
        total={5}
        onChange={vi.fn()}
        aria-label="pagination"
      />,
    );
    expect(
      screen.getByLabelText('pagination item 1 active'),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('pagination item 5')).toBeInTheDocument();
  });

  it('calls onChange when a page is selected', () => {
    const onChange = vi.fn();
    render(
      <Pagination
        showControls
        page={1}
        total={5}
        onChange={onChange}
        aria-label="pagination"
      />,
    );
    fireEvent.click(screen.getByLabelText('pagination item 3'));
    expect(onChange).toHaveBeenCalledWith(3);
  });

  it('renders bordered variant with controls', () => {
    render(
      <Pagination
        showControls
        variant="bordered"
        size="sm"
        page={2}
        total={8}
        aria-label="pagination"
      />,
    );
    expect(
      screen.getByLabelText('pagination item 2 active'),
    ).toBeInTheDocument();
  });
});
