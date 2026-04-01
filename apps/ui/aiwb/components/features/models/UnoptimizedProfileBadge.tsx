// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { IconAlertTriangle } from '@tabler/icons-react';

type UnoptimizedProfileBadgeProps = {
  label: string;
};

/** Badge for unoptimized performance profile (Deploy drawer and AIM details). */
export const UnoptimizedProfileBadge = ({
  label,
}: UnoptimizedProfileBadgeProps) => {
  return (
    <span className="flex items-center gap-1.5 text-tiny shrink-0 whitespace-nowrap">
      <span className="text-warning">
        <IconAlertTriangle size={14} aria-hidden />
      </span>
      <span className="text-foreground">{label}</span>
    </span>
  );
};
