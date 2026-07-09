// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import type { ReactNode } from 'react';

type MockButtonProps = {
  children?: ReactNode;
  onPress?: () => void;
  onClick?: () => void;
  isDisabled?: boolean;
  disabled?: boolean;
  startContent?: ReactNode;
  endContent?: ReactNode;
  [key: string]: unknown;
};

export function MockButton({
  children,
  onPress,
  onClick,
  isDisabled,
  disabled,
  startContent,
  endContent,
  ...props
}: MockButtonProps) {
  return (
    <button
      onClick={onPress ?? onClick}
      disabled={isDisabled ?? disabled}
      {...props}
    >
      {startContent}
      {children}
      {endContent}
    </button>
  );
}

export function MockButtonGroup({ children }: { children?: ReactNode }) {
  return <fieldset>{children}</fieldset>;
}

export function withMockAmdenterpriseaiButtonStubs<
  T extends Record<string, unknown>,
>(actual: T) {
  return {
    ...actual,
    Button: MockButton,
    ButtonGroup: MockButtonGroup,
  };
}
