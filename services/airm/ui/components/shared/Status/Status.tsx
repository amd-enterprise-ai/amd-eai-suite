// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';
import {
  Chip,
  Tooltip,
  Popover,
  PopoverContent,
  PopoverTrigger,
  cn,
} from '@heroui/react';
import {
  IconInfoCircle,
  IconCircleCheck,
  IconCircleX,
  IconAlertTriangle,
  IconLoaderQuarter,
} from '@tabler/icons-react';
import { Color } from '@/types/colors';
import { Size } from '@/types/sizes';

export type StatusProps = {
  label: string;
  color?: Color;
  icon?: React.ComponentType<{
    size?: number;
    role?: string;
    className?: string;
  }>;
  intent?: Intent;
  helpContent?: React.ReactNode;
  isClickable?: boolean;
  isTextColored?: boolean;
  isSubtle?: boolean;
  isShowBackground?: boolean;
  size?: Size;
};

export enum Intent {
  SUCCESS = 'success',
  WARNING = 'warning',
  DANGER = 'danger',
  PENDING = 'pending',
}

// Constants
const INTENT_TO_PROPS = {
  [Intent.SUCCESS]: {
    color: 'success' as Color,
    icon: IconCircleCheck,
  },
  [Intent.WARNING]: {
    color: 'warning' as Color,
    icon: IconAlertTriangle,
  },
  [Intent.DANGER]: {
    color: 'danger' as Color,
    icon: IconCircleX,
  },
  [Intent.PENDING]: {
    color: 'primary' as Color,
    icon: IconLoaderQuarter,
  },
} as const;

const HOVER_DECORATION_CLASSES: Record<Exclude<Color, undefined>, string> = {
  default: 'group-hover:decoration-foreground',
  primary: 'group-hover:decoration-primary',
  secondary: 'group-hover:decoration-secondary',
  warning: 'group-hover:decoration-warning',
  success: 'group-hover:decoration-success',
  danger: 'group-hover:decoration-danger',
};

const SIZE_TO_ICON_SIZE: Record<Exclude<Size, undefined>, number> = {
  sm: 14,
  md: 20,
  lg: 24,
};

const SIZE_TO_INFO_ICON_SIZE: Record<Exclude<Size, undefined>, number> = {
  sm: 14,
  md: 16,
  lg: 18,
};

const COLOR_CLASSES: Record<Exclude<Color, undefined>, string> = {
  default: 'text-foreground',
  primary: 'text-primary',
  secondary: 'text-secondary',
  warning: 'text-warning',
  success: 'text-success',
  danger: 'text-danger',
};

const TEXT_COLOR_SUBTLE_CLASSES: Record<Exclude<Color, undefined>, string> = {
  default: 'text-foreground/50',
  primary: 'text-primary/60',
  secondary: 'text-secondary/60',
  warning: 'text-warning/60',
  success: 'text-success/60',
  danger: 'text-danger/60',
};

const ICON_COLOR_SUBTLE_CLASSES: Record<Exclude<Color, undefined>, string> = {
  default: 'text-foreground/50',
  primary: 'text-primary/90',
  secondary: 'text-secondary/80',
  warning: 'text-warning/80',
  success: 'text-success/80',
  danger: 'text-danger/90',
};

const DECORATION_COLOR_OPACITY_CLASSES: Record<
  Exclude<Color, undefined>,
  string
> = {
  default: 'decoration-foreground/50',
  primary: 'decoration-primary/50',
  secondary: 'decoration-secondary/50',
  warning: 'decoration-warning/50',
  success: 'decoration-success/50',
  danger: 'decoration-danger/50',
};

// Helper functions
type TextColorResult = {
  textColorClasses: Record<string, boolean>;
  iconColorClasses: Record<string, boolean>;
};

const getTextColorClasses = (
  color: Color,
  isSubtle: boolean,
  isTextColored: boolean,
): TextColorResult => {
  if (!color) return { textColorClasses: {}, iconColorClasses: {} };
  const colorKey = color as Exclude<Color, undefined>;

  if (isSubtle) {
    return {
      textColorClasses: isTextColored
        ? { [TEXT_COLOR_SUBTLE_CLASSES[colorKey]]: true }
        : { [TEXT_COLOR_SUBTLE_CLASSES.default]: true },
      iconColorClasses: { [ICON_COLOR_SUBTLE_CLASSES[colorKey]]: true },
    };
  }

  return {
    textColorClasses: {},
    iconColorClasses: { [COLOR_CLASSES[colorKey]]: true },
  };
};

const getDecorationClasses = (
  color: Color,
  helpContent: React.ReactNode,
  isTextColored: boolean,
  isClickable: boolean,
): Record<string, boolean> => {
  const hasHelp = !!helpContent;
  const result: Record<string, boolean> = {};

  if (hasHelp) {
    result['underline decoration-dotted underline-offset-2'] = true;
    if (isTextColored && color) {
      const colorKey = color as Exclude<Color, undefined>;
      result[DECORATION_COLOR_OPACITY_CLASSES[colorKey]] = true;
    } else {
      result[DECORATION_COLOR_OPACITY_CLASSES.default] = true;
    }

    if (isClickable) {
      if (isTextColored && color) {
        const colorKey = color as Exclude<Color, undefined>;
        result[HOVER_DECORATION_CLASSES[colorKey]] = true;
      } else {
        result['group-hover:decoration-foreground'] = true;
      }
    }
  }

  return result;
};

const StatusWrapper: React.FC<{
  helpContent?: React.ReactNode;
  isClickable: boolean;
  children: React.ReactNode;
}> = ({ helpContent, isClickable, children }) => {
  if (!helpContent) {
    return <>{children}</>;
  }

  if (isClickable) {
    return (
      <Popover placement="bottom">
        <PopoverTrigger>{children}</PopoverTrigger>
        <PopoverContent>{helpContent}</PopoverContent>
      </Popover>
    );
  }

  return (
    <Tooltip placement="bottom" content={helpContent}>
      {children}
    </Tooltip>
  );
};

const Status: React.FC<StatusProps> = ({
  label,
  color: colorProp,
  icon: iconProp,
  intent,
  helpContent,
  isClickable = false,
  isTextColored = false,
  isSubtle = false,
  isShowBackground = false,
  size = 'md',
}) => {
  // Resolve color and icon from props or intent
  const intentDefaults = intent ? INTENT_TO_PROPS[intent] : null;
  const color = colorProp ?? intentDefaults?.color ?? 'primary';
  const IconComponent = iconProp ?? intentDefaults?.icon ?? null;
  const hasHelp = !!helpContent;

  const { textColorClasses, iconColorClasses } = getTextColorClasses(
    color,
    isSubtle,
    isTextColored,
  );

  return (
    <StatusWrapper helpContent={helpContent} isClickable={isClickable}>
      <Chip
        color={isTextColored ? color : 'default'}
        variant={isShowBackground ? 'flat' : 'light'}
        size={size}
        classNames={{
          base: cn({
            'gap-0.25': true,
            'px-0': !isShowBackground,
            'px-1.5': isShowBackground,
            'cursor-pointer': hasHelp && isClickable,
            'cursor-help': hasHelp && !isClickable,
            group: hasHelp && isClickable,
          }),
          content: cn({
            ...getDecorationClasses(
              color,
              helpContent,
              isTextColored,
              isClickable,
            ),
            ...textColorClasses,
          }),
        }}
        startContent={
          <div className={cn(iconColorClasses)}>
            {IconComponent && (
              <IconComponent
                size={SIZE_TO_ICON_SIZE[size ?? 'md']}
                role="img"
                className={cn({
                  'animate-spin': IconComponent === IconLoaderQuarter,
                })}
              />
            )}
          </div>
        }
        endContent={
          hasHelp ? (
            <IconInfoCircle
              role="img"
              className="text-foreground/50"
              size={SIZE_TO_INFO_ICON_SIZE[size ?? 'md']}
            />
          ) : undefined
        }
      >
        {label}
      </Chip>
    </StatusWrapper>
  );
};

export default Status;
