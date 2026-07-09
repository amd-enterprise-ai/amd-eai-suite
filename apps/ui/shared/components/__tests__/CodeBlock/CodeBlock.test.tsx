// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';
import { render, screen } from '@testing-library/react';
import { CodeBlock } from '@amdenterpriseai/components';

describe('CodeBlock adapter', () => {
  it('renders its children', () => {
    render(<CodeBlock>const answer = 42;</CodeBlock>);
    expect(screen.getByText('const answer = 42;')).toBeInTheDocument();
  });

  it('renders a code element by default', () => {
    const { container } = render(<CodeBlock>inline</CodeBlock>);
    expect(container.querySelector('code')).toBeInTheDocument();
  });

  it('renders a pre element when as="pre"', () => {
    const { container } = render(<CodeBlock as="pre">block</CodeBlock>);
    expect(container.querySelector('pre')).toBeInTheDocument();
  });

  it('passes a custom className through to the rendered element', () => {
    const { container } = render(
      <CodeBlock className="custom-class">styled</CodeBlock>,
    );
    expect(container.firstChild).toHaveClass('custom-class');
  });
});
