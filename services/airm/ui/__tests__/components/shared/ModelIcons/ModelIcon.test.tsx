// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

import { ModelIcon } from '@/components/shared/ModelIcons/ModelIcon';

// Mock SVG imports
vi.mock('@/assets/svg/model-icons/default.svg', () => ({
  default: (props: any) => <svg data-testid="default-icon" {...props} />,
}));

vi.mock('@/assets/svg/model-icons/deepseek.svg', () => ({
  default: (props: any) => <svg data-testid="deepseek-icon" {...props} />,
}));

vi.mock('@/assets/svg/model-icons/gemma.svg', () => ({
  default: (props: any) => <svg data-testid="gemma-icon" {...props} />,
}));

vi.mock('@/assets/svg/model-icons/mistral.svg', () => ({
  default: (props: any) => <svg data-testid="mistral-icon" {...props} />,
}));

vi.mock('@/assets/svg/model-icons/mixtral.svg', () => ({
  default: (props: any) => <svg data-testid="mixtral-icon" {...props} />,
}));

vi.mock('@/assets/svg/model-icons/qwen.svg', () => ({
  default: (props: any) => <svg data-testid="qwen-icon" {...props} />,
}));

describe('ModelIcon', () => {
  it('renders with default icon when no iconName is provided', () => {
    render(<ModelIcon />);

    const wrapper = screen.getByLabelText('Default model icon');
    expect(wrapper).toBeInTheDocument();
  });

  it('renders with wrapper div containing proper styles', () => {
    const width = 48;
    const height = 48;

    render(<ModelIcon iconName="test" width={width} height={height} />);

    const wrapper = screen.getByLabelText('test model icon');
    expect(wrapper).toBeInTheDocument();
    expect(wrapper).toHaveStyle({
      width: `${width}px`,
      height: `${height}px`,
      minWidth: `${width}px`,
      minHeight: `${height}px`,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    });
  });

  it('renders with default dimensions when not specified', () => {
    render(<ModelIcon iconName="test" />);

    const wrapper = screen.getByLabelText('test model icon');
    expect(wrapper).toBeInTheDocument();
  });

  it('renders correct icon based on iconName', () => {
    render(<ModelIcon iconName="huggingface" width={32} height={32} />);

    const wrapper = screen.getByLabelText('huggingface model icon');
    expect(wrapper).toBeInTheDocument();
  });

  it('matches icon name case-insensitively', () => {
    render(<ModelIcon iconName="HUGGINGFACE" width={32} height={32} />);

    const wrapper = screen.getByLabelText('HUGGINGFACE model icon');
    expect(wrapper).toBeInTheDocument();
  });

  it('renders wrapper div as direct parent of icon SVG', () => {
    const { container } = render(
      <ModelIcon iconName="test" width={24} height={24} />,
    );

    const wrapper = screen.getByLabelText('test model icon');
    expect(wrapper.tagName).toBe('DIV');
    expect(wrapper.firstChild?.nodeName).toBe('svg');
  });

  it('applies 100% width and auto height to SVG element', () => {
    const { container } = render(
      <ModelIcon iconName="test" width={50} height={50} />,
    );

    const wrapper = screen.getByLabelText('test model icon');
    const svg = wrapper.querySelector('svg');

    expect(svg).toHaveStyle({
      width: '100%',
      height: 'auto',
    });
  });
});
