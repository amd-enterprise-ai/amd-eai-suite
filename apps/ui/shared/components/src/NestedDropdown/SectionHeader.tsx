// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { DropdownItem } from './types';

interface SectionHeaderProps {
  action: DropdownItem;
}

export const SectionHeader = ({ action }: SectionHeaderProps) => {
  return (
    <div
      className="px-1.5 py-2 pointer-events-none"
      data-testid={`section-${action.key}`}
      role="presentation"
    >
      <div className="text-tiny font-semibold text-foreground-500 uppercase">
        {action.label}
      </div>
      {action.description && (
        <div className="text-tiny text-foreground-400 mt-0.5">
          {action.description}
        </div>
      )}
    </div>
  );
};
