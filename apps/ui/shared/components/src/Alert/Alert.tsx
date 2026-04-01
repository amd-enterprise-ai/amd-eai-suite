// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Alert as HeroUIAlert, AlertProps, cn } from '@heroui/react';
import {
  IconAlertTriangle,
  IconCircleCheck,
  IconInfoCircle,
} from '@tabler/icons-react';

/**
 * HeroUI Alert wraps the icon in an element that receives classNames.alertIcon.
 * We set fill-none there so stroke-based icons (e.g. Tabler) render correctly;
 * otherwise theme/global SVG fill can make them look solid.
 */
const getIconForColor = (
  color: AlertProps['color'],
  size: number = 16,
): React.ReactNode => {
  switch (color) {
    case 'danger':
    case 'warning':
      return <IconAlertTriangle size={size} />;
    case 'success':
      return <IconCircleCheck size={size} />;
    case 'default':
    case 'primary':
    case 'secondary':
    default:
      return <IconInfoCircle size={size} />;
  }
};

export const Alert: React.FC<AlertProps> = ({
  color,
  icon,
  classNames,
  ...props
}) => {
  const defaultIcon = icon === undefined ? getIconForColor(color) : icon;

  return (
    <HeroUIAlert
      color={color}
      icon={defaultIcon}
      classNames={{
        ...classNames,
        alertIcon: cn('fill-none', classNames?.alertIcon),
      }}
      {...props}
    />
  );
};

export default Alert;
