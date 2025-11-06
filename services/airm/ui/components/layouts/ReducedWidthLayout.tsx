// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { cn } from '@heroui/react';
import React from 'react';

type Props = {
  children: React.ReactNode;
  padded?: boolean;
  className?: string;
};

const ReducedWidthLayout = ({ children, className, padded = true }: Props) => {
  return (
    <div className={cn('max-w-[1024px]', padded && 'py-8', className)}>
      {children}
    </div>
  );
};

export default ReducedWidthLayout;
