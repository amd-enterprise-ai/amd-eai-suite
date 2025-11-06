// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Input, Slider } from '@heroui/react';
import { forwardRef, useCallback, useRef, useState } from 'react';

interface Props {
  defaultValue?: number;
  min: number;
  max: number;
  id: string;
  ariaLabel: string;
  value?: number;
  disabled?: boolean;
  step?: number;
  onChange?: (event: React.ChangeEvent<HTMLInputElement>) => void;
}

const getBoundedValue = (value: number, min: number, max: number): number => {
  if (value > max) {
    return max;
  } else if (value < min) {
    return min;
  }
  return value;
};

export const SliderInput = forwardRef<HTMLInputElement, Props>((props, ref) => {
  const {
    id,
    ariaLabel,
    defaultValue = 0,
    min = 0,
    max = 100,
    step,
    disabled,
    onChange,
  } = props;

  const handleInputChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      onChange?.(event);
      if (!event.target.value) {
        setVal(min);
        onChange?.(event);
      }
      let parsedVal = parseFloat(event.target.value);
      setVal(getBoundedValue(parsedVal, min, max));
    },
    [min, max, onChange],
  );

  const handleSliderChange = useCallback(
    (value: number | number[]) => {
      let val = Array.isArray(value) ? value[0] : value;
      const boundedVal = getBoundedValue(val, min, max);
      setVal(boundedVal);
      onChange?.({
        target: {
          name: id,
          value: val,
        },
      } as unknown as React.ChangeEvent<HTMLInputElement>);
    },
    [min, max, id, onChange],
  );

  const [val, setVal] = useState<number>(() =>
    getBoundedValue(props.value ?? defaultValue, min, max),
  );

  const prevValueRef = useRef<number | undefined>(props?.value);

  if (props.value !== prevValueRef.current) {
    prevValueRef.current = props.value;
    setVal(getBoundedValue(props.value ?? defaultValue, min, max));
  }

  return (
    <div className="flex gap-2 items-center">
      <Slider
        aria-label={ariaLabel}
        color="primary"
        minValue={min}
        maxValue={max}
        value={val}
        onChange={handleSliderChange}
        step={step}
        isDisabled={disabled}
        classNames={{
          thumb: 'w-4 h-4 after:w-3 after:h-3',
        }}
      />
      <Input
        ref={ref}
        classNames={{
          base: 'max-w-20',
        }}
        type="number"
        step={step?.toString()}
        isDisabled={disabled}
        {...props}
        defaultValue={props.defaultValue?.toString()}
        onChange={handleInputChange}
        label={null}
        value={val.toString()}
      />
    </div>
  );
});

SliderInput.displayName = 'SliderInput';

export default SliderInput;
