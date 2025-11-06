// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Spinner } from '@heroui/react';
import React, { ReactNode } from 'react';

import { StatusBadgeVariant } from '@/types/data-table/status-variant';

interface StatusHeaderDisplayProps {
  variants: Record<string, StatusBadgeVariant>;
  type: string;
}

/**
 * Displays a status badge with background color styling, typically used in headers.
 * This component applies background colors based on the status variant color and includes
 * proper border styling for visual consistency.
 *
 * @example
 * ```tsx
 * const statusVariants = getWorkloadStatusVariants(t);
 *
 * <StatusHeaderDisplay
 *   type={workload.status}
 *   variants={statusVariants}
 * />
 * ```
 *
 * @param type - The key of the variant to display.
 */
const StatusHeaderDisplay: React.FC<StatusHeaderDisplayProps> = ({
  variants,
  type,
}) => {
  // Handle case where variant doesn't exist
  const variant = variants[type];
  if (!variant) {
    return (
      <div className="px-3 py-1 rounded-lg dark:bg-danger-800 bg-danger-100">
        <span className="flex font flex-nowrap gap-1 items-center text-danger">
          {type}!
        </span>
      </div>
    );
  }

  const {
    label,
    icon: iconSource,
    color = 'default',
    textColor: labelColorName = '',
  } = variant;

  const getBackgroundClass = (color?: string) => {
    switch (color) {
      case 'success':
        return 'dark:bg-success-800 bg-success-100';
      case 'primary':
        return 'dark:bg-primary-800 bg-primary-100';
      case 'warning':
        return 'dark:bg-warning-800 bg-warning-100';
      case 'danger':
        return 'dark:bg-danger-800 bg-danger-100';
      default:
        return 'dark:bg-default-800 bg-default-100';
    }
  };

  const iconStylingClass =
    color && `text-${color}` + (color === 'default' ? '-500' : '');

  const labelStylingClass =
    labelColorName &&
    `text-${labelColorName}` + (labelColorName === 'default' ? '-500' : '');

  let iconElement: ReactNode;

  if (iconSource === 'spinner') {
    iconElement = <Spinner size="sm" color={color} className="scale-75" />;
  } else {
    const IconComponent = iconSource;
    iconElement = <IconComponent size="20" className={iconStylingClass} />;
  }

  return (
    <div className={`px-3 py-1 rounded-lg ${getBackgroundClass(color)}`}>
      <span
        className={`flex font flex-nowrap gap-1 items-center ${labelStylingClass}`}
      >
        {iconElement}
        {label}
      </span>
    </div>
  );
};

export default StatusHeaderDisplay;
