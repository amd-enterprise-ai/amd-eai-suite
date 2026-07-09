// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';
import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import { Select, SelectItem } from '@amdenterpriseai/components';

describe('Select adapter', () => {
  it('exposes Item as a static property', () => {
    expect(Select.Item).toBe(SelectItem);
  });

  it('renders single-select with selectedKeys', () => {
    render(
      <Select label="Fruit" selectedKeys={['apple']} aria-label="Fruit">
        <SelectItem key="apple">Apple</SelectItem>
      </Select>,
    );
    expect(screen.getByRole('button', { name: /Fruit/ })).toBeInTheDocument();
  });

  it('accepts onSelectionChange', () => {
    const onSelectionChange = vi.fn();
    render(
      <Select
        label="Color"
        onSelectionChange={onSelectionChange}
        aria-label="Color"
      >
        <SelectItem key="red">Red</SelectItem>
      </Select>,
    );
    expect(screen.getByRole('button', { name: /Color/ })).toBeInTheDocument();
  });

  it('renders multi-select', () => {
    render(
      <Select
        label="Tags"
        selectionMode="multiple"
        selectedKeys={['a']}
        aria-label="Tags"
      >
        <SelectItem key="a">Alpha</SelectItem>
      </Select>,
    );
    expect(screen.getByRole('button', { name: /Tags/ })).toBeInTheDocument();
  });

  it('renders compound syntax', () => {
    render(
      <Select label="Size" selectedKeys={['md']} aria-label="Size">
        <Select.Item key="md">Medium</Select.Item>
      </Select>,
    );
    expect(screen.getByRole('button', { name: /Size/ })).toBeInTheDocument();
  });
});
