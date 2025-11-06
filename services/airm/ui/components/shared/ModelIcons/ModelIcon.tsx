// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import React from 'react';

import { ModelIconType, ModelIcons } from './index';

interface ModelIconProps {
  iconName?: string;
  width?: number;
  height?: number;
}

export const ModelIcon: React.FC<ModelIconProps> = ({
  iconName,
  width,
  height,
}) => {
  const iconKey = Object.keys(ModelIcons).find((key) =>
    iconName?.toLowerCase().includes(key.toLowerCase()),
  ) as ModelIconType;

  const IconComponent = ModelIcons[iconKey] || ModelIcons.default;

  const iconWrapperProps = {
    'aria-label': `${iconName || 'Default'} model icon`,
    style: {
      width: `${width}px`,
      height: `${height}px`,
      minWidth: `${width}px`,
      minHeight: `${height}px`,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    },
  };

  return (
    <div {...iconWrapperProps}>
      <IconComponent style={{ width: '100%', height: 'auto' }} />
    </div>
  );
};
