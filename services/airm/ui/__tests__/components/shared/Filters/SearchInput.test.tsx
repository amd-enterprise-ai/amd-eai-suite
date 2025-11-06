// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { act, fireEvent, render, screen } from '@testing-library/react';

import SearchInput from '@/components/shared/Filters/SearchInput';

import { vi } from 'vitest';

// Mock debounce to execute immediately for testing purposes
vi.mock('lodash', async () => {
  const actual = await vi.importActual('lodash');
  return {
    ...(actual as object),
    debounce: (fn: Function) => fn,
  };
});

describe('SearchInput Component', () => {
  it('renders correctly with default props', () => {
    render(<SearchInput />);
    const inputElement = screen.getByRole('textbox');
    expect(inputElement).toBeInTheDocument();
  });

  it('renders with the correct placeholder', () => {
    const placeholder = 'Search items...';
    render(<SearchInput placeholder={placeholder} />);
    const inputElement = screen.getByPlaceholderText(placeholder);
    expect(inputElement).toBeInTheDocument();
  });

  it('applies the correct size class', () => {
    const { container } = render(<SearchInput size="sm" />);
    const inputWrapper = container.querySelector('.w-54');
    expect(inputWrapper).toBeInTheDocument();
  });

  it('initializes with the default value', () => {
    const defaultValue = 'initial search';
    render(<SearchInput defaultValue={defaultValue} />);
    const inputElement = screen.getByRole('textbox') as HTMLInputElement;
    expect(inputElement.value).toBe(defaultValue);
  });

  it('updates internal value when the input changes', () => {
    render(<SearchInput />);
    const inputElement = screen.getByRole('textbox') as HTMLInputElement;

    fireEvent.change(inputElement, { target: { value: 'new search' } });

    expect(inputElement.value).toBe('new search');
  });

  it('calls onValueChange when the input changes', () => {
    const onValueChangeMock = vi.fn();
    render(<SearchInput onValueChange={onValueChangeMock} />);
    const inputElement = screen.getByRole('textbox');

    fireEvent.change(inputElement, { target: { value: 'test search' } });

    expect(onValueChangeMock).toHaveBeenCalledWith('test search');
  });

  it('updates value when defaultValue prop changes', () => {
    const { rerender } = render(<SearchInput defaultValue="initial" />);
    const inputElement = screen.getByRole('textbox') as HTMLInputElement;
    expect(inputElement.value).toBe('initial');

    rerender(<SearchInput defaultValue="updated" />);
    expect(inputElement.value).toBe('updated');
  });

  it('uses debounced function when disableDebounce is false', () => {
    const onValueChangeMock = vi.fn();

    render(
      <SearchInput
        onValueChange={onValueChangeMock}
        disableDebounce={false}
        delay={300}
      />,
    );

    const inputElement = screen.getByRole('textbox');
    fireEvent.change(inputElement, { target: { value: 'debounced search' } });

    expect(onValueChangeMock).toHaveBeenCalledWith('debounced search');
  });

  it('clears the input when the clear button is clicked', () => {
    render(<SearchInput defaultValue="test value" />);
    const inputElement = screen.getByRole('textbox') as HTMLInputElement;
    expect(inputElement.value).toBe('test value');

    // Find and click the clear button
    const clearButton = screen.getByLabelText('actions.clear.title');
    fireEvent.click(clearButton);

    expect(inputElement.value).toBe('');
  });
});
