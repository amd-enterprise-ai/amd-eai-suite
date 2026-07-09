// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';
import { render, screen } from '@testing-library/react';
import { Button, ButtonGroup } from '@amdenterpriseai/components';

describe('Button adapter', () => {
  it('renders with children', () => {
    render(<Button data-testid="btn">Click me</Button>);
    expect(screen.getByTestId('btn')).toHaveTextContent('Click me');
  });

  it('passes color prop', () => {
    render(
      <Button color="primary" data-testid="btn">
        Primary
      </Button>,
    );
    expect(screen.getByTestId('btn')).toBeInTheDocument();
  });

  it('passes variant prop', () => {
    render(
      <Button variant="flat" data-testid="btn">
        Flat
      </Button>,
    );
    expect(screen.getByTestId('btn')).toBeInTheDocument();
  });

  it('passes isDisabled prop', () => {
    render(
      <Button isDisabled data-testid="btn">
        Disabled
      </Button>,
    );
    expect(screen.getByTestId('btn')).toBeDisabled();
  });

  it('accepts onPress prop without error', () => {
    const handlePress = vi.fn();
    const { unmount } = render(
      <Button onPress={handlePress} data-testid="btn">
        Press me
      </Button>,
    );
    expect(screen.getByTestId('btn')).toBeInTheDocument();
    unmount();
  });
});

describe('ButtonGroup adapter', () => {
  it('renders children buttons', () => {
    render(
      <ButtonGroup>
        <Button data-testid="btn-a">A</Button>
        <Button data-testid="btn-b">B</Button>
      </ButtonGroup>,
    );
    expect(screen.getByTestId('btn-a')).toBeInTheDocument();
    expect(screen.getByTestId('btn-b')).toBeInTheDocument();
  });
});
