// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Chip, ChipProps, cn } from '@heroui/react';
import React from 'react';

import { Color } from '@/types/colors';
import { Size } from '@/types/sizes';

export interface InlineBadgeProps
  extends Omit<ChipProps, 'size' | 'color' | 'ref'> {
  size?: Size;
  color?: Color;
  showOutline?: boolean;
  isOneChar?: boolean;
  isInvisible?: boolean;
  disableAnimation?: boolean;
  hideText?: boolean;
}

export const InlineBadge = ({
  size,
  color,
  showOutline = true,
  children,
  disableAnimation = false,
  hideText = false,
  isInvisible = false,
  isOneChar = false,
  tabIndex = -1,
  className,
  ...rest
}: InlineBadgeProps): React.JSX.Element => {
  const startContent =
    typeof children === 'string' ? (
      <span className={cn('grow text-center', { hidden: hideText })}>
        {isOneChar ? children.slice(0, 1).toUpperCase() : children}
      </span>
    ) : (
      children
    );

  // Build custom classes based on variants
  const sizeClasses = {
    sm: 'min-w-6 px-1 h-6 text-tiny',
    md: 'min-w-7 px-1 h-7 text-small',
    lg: 'min-w-8 px-2 h-8 text-medium',
  };

  const outlineClasses = showOutline
    ? 'border-2 border-background'
    : 'border-0 border-transparent';

  const animationClasses = disableAnimation
    ? ''
    : 'origin-center transition-transform-opacity !ease-soft-spring !duration-300 data-[invisible=true]:opacity-0';

  const customClassName = cn(
    sizeClasses[size || 'md'],
    outlineClasses,
    animationClasses,
    className,
  );

  return (
    <Chip
      color={color}
      variant="flat"
      startContent={startContent}
      data-invisible={isInvisible}
      classNames={{ content: 'hidden' }}
      tabIndex={tabIndex}
      className={customClassName}
      {...rest}
    />
  );
};
