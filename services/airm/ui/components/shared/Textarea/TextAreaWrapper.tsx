// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

// FIXME: Refactor or remove?
import { Chip, Textarea } from '@heroui/react';
import React, { useState } from 'react';

import { InputWrapper } from '../Input/InputWrapper';

interface TextAreaWrapperProps {
  label: string;
  ariaLabel: string;
  value: string;
  onChange: (value: string) => void;
  onValidationError?: (error: string | null) => void;
  tooltip?: string;
  rows?: number;
  disabled?: boolean;
  description: string;
  validate?: (value: string) => boolean;
  chipMessages?: { insertText: string; userMessage: string }[];
  placeholder?: string;
  validationErrorMessage?: string;
}

export const TextAreaWrapper: React.FC<TextAreaWrapperProps> = ({
  label,
  ariaLabel,
  value,
  onChange,
  onValidationError,
  tooltip,
  rows = 6,
  placeholder,
  disabled = false,
  description,
  validate,
  validationErrorMessage = 'Invalid input',
  chipMessages,
}) => {
  const [inputValue, setInputValue] = useState(value);
  const [prevValue, setPrevValue] = useState(value);
  const [isValid, setIsValid] = useState(true);

  const handleValidationAndStateUpdate = (val: string) => {
    setInputValue(val);

    if (disabled) return;

    if (validate) {
      const valid = validate(val);
      setIsValid(valid);

      if (valid) {
        onChange(val);
      }

      if (onValidationError) {
        onValidationError(valid ? null : label);
      }
    } else {
      onChange(val);
    }
  };

  if (value !== prevValue) {
    setPrevValue(value);
    handleValidationAndStateUpdate(value);
  }

  const handleInputEvent = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    handleValidationAndStateUpdate(val);
  };

  const insertText = (text: string) => {
    handleValidationAndStateUpdate(inputValue + text);
  };

  return (
    <InputWrapper label={label} tooltip={tooltip} description={description}>
      <Textarea
        aria-label={ariaLabel}
        value={inputValue}
        onChange={(e) => handleInputEvent(e)}
        isDisabled={disabled}
        isInvalid={!isValid}
        placeholder={placeholder}
        errorMessage={validationErrorMessage}
        minRows={rows}
        maxRows={rows}
        onKeyDown={(e) => {
          e.stopPropagation();
        }}
      />
      {chipMessages && (
        <div className="flex gap-2">
          {chipMessages.map((chip, index) => (
            <Chip
              size="sm"
              className="bg-default-200 cursor-pointer"
              isDisabled={inputValue.includes(chip.insertText)}
              onClick={() => insertText(chip.insertText)}
              key={index}
            >
              {chip.userMessage}
            </Chip>
          ))}
        </div>
      )}
    </InputWrapper>
  );
};

export default TextAreaWrapper;
