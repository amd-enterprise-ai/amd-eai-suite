// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { IconAlertTriangle, IconInfoCircle } from '@tabler/icons-react';

import { ActionFieldHintType } from '@amdenterpriseai/types';

interface ActionHintsListProps {
  hints: Array<{ type: ActionFieldHintType; message: string }>;
}

export const ActionHintsList = ({ hints }: ActionHintsListProps) => {
  if (hints.length === 0) return null;

  return (
    <div className="flex flex-col gap-1 mt-1 text-xs">
      {hints.map((h) => (
        <div className="flex items-center gap-1" key={h.message}>
          {h.type === ActionFieldHintType.INFO && (
            <IconInfoCircle className="text-info" />
          )}
          {h.type === ActionFieldHintType.WARNING && (
            <IconAlertTriangle className="text-warning" />
          )}
          {h.type === ActionFieldHintType.ERROR && (
            <IconAlertTriangle className="text-danger" />
          )}
          <span>{h.message}</span>
        </div>
      ))}
    </div>
  );
};
