// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { cn } from '@heroui/react';
import { Spinner } from '@amdenterpriseai/components';

type PageLoaderProps = {
  label?: string;
  testId?: string;
  className?: string;
};

export const PageLoader: React.FC<PageLoaderProps> = ({
  label,
  testId,
  className,
}) => (
  <div
    className={cn('flex flex-col items-center justify-center gap-2', className)}
    data-testid={testId}
  >
    <Spinner size="lg" color="primary" />
    {label && <p className="text-center text-sm text-default-500">{label}</p>}
  </div>
);
