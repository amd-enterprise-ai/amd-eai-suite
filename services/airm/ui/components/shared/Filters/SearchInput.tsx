// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Input, InputProps } from '@heroui/react';
import { IconSearch } from '@tabler/icons-react';
import {
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useState,
} from 'react';
import React, { forwardRef } from 'react';
import { debounce } from 'lodash';
import ClearSingleFilterButton from './ClearSingleFilterButton';

const sizeToClassName = {
  sm: 'w-54',
  md: 'w-96',
  lg: 'w-1/2',
  full: 'w-full',
} as const;

type SearchInputSize = keyof typeof sizeToClassName;

interface SearchInputProps extends Omit<InputProps, 'size'> {
  placeholder?: string;
  canClear?: boolean;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  delay?: number;
  disableDebounce?: boolean;
  size?: SearchInputSize;
}

/**
 * `SearchInput` is a React functional component that provides a customizable search input field.
 * It features debounced value changes to optimize performance, clearable input, and various size options.
 *
 * @param {SearchInputProps} props - The props for the component.
 * @param {string} [props.placeholder] - Placeholder text for the input.
 * @param {string} [props.defaultValue=''] - Default value for the input.
 * @param {'sm' | 'md' | 'lg' | 'full'} [props.size='full'] - Size of the input.
 * @param {(value: string) => void} [props.onValueChange] - Callback function triggered when the input value changes.
 * @param {number} [props.delay=500] - Delay in milliseconds for debouncing the onValueChange callback.
 * @param {boolean} [props.disableDebounce=false] - Disables debouncing if set to true.
 * @returns {JSX.Element} The rendered search input component.
 */
const SearchInput = forwardRef<{ clear: () => void }, SearchInputProps>(
  (
    {
      placeholder,
      defaultValue = '',
      onValueChange,
      size = 'sm',
      delay = 500,
      disableDebounce = false,
      ...other
    },
    ref,
  ) => {
    const [internalValue, setInternalValue] = useState<string>(defaultValue);
    const inputRef = React.useRef<HTMLInputElement>(null);

    useEffect(() => {
      if (defaultValue) setInternalValue(defaultValue);
    }, [defaultValue]);

    // Imperative handle to allow parent to clear the input value
    useImperativeHandle(
      ref,
      () => ({
        clear: () => {
          setInternalValue('');
          // Optionally also clear the actual input element
          if (inputRef.current) {
            inputRef.current.value = '';
          }
        },
      }),
      [],
    );

    const debouncedOnValueChange = useMemo(() => {
      if (!onValueChange) return undefined;
      if (disableDebounce) return onValueChange;
      return debounce(onValueChange, delay);
    }, [onValueChange, delay, disableDebounce]);

    const handleValueChange = useCallback(
      (newValue: string) => {
        setInternalValue(newValue);
        debouncedOnValueChange?.(newValue);
      },
      [debouncedOnValueChange],
    );
    return (
      <Input
        ref={inputRef}
        placeholder={placeholder}
        size="md"
        radius="md"
        value={internalValue}
        onValueChange={handleValueChange}
        classNames={{ inputWrapper: 'pr-8', base: sizeToClassName[size] }}
        variant="bordered"
        startContent={<IconSearch size={16} />}
        isClearable={false}
        endContent={
          internalValue.length ? (
            <ClearSingleFilterButton onPress={() => handleValueChange('')} />
          ) : null
        }
        {...other}
      />
    );
  },
);

SearchInput.displayName = 'SearchInput';

export default SearchInput;
