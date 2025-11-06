// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

/**
 * Drag overlay component that shows when files are being dragged over the upload area
 */
import { cn } from '@heroui/react';
import { IconFile, IconX } from '@tabler/icons-react';
import { memo } from 'react';

import type { TFunction } from 'next-i18next';

const DragOverlay = memo(
  ({
    canDrop,
    multiple,
    t,
  }: {
    canDrop: boolean;
    multiple: boolean;
    t: TFunction;
  }) => (
    <div
      className={cn(
        'absolute inset-0 z-10 rounded top-0.5 left-0.5 right-0.5 bottom-0.5 border-1 border-dashed flex flex-col items-center justify-center transition-colors gap-2',
        canDrop
          ? 'bg-background/80 border-success-400 text-success-400'
          : 'bg-background/80 border-danger-400 text-danger-400',
      )}
    >
      {canDrop ? (
        <IconFile size={32} className="text-inherit" />
      ) : (
        <IconX size={32} className="text-inherit" />
      )}
      <span className="text-sm text-inherit">
        {canDrop
          ? t('drop', { count: +multiple + 1 })
          : t('dropFail', { count: +multiple + 1 })}
      </span>
    </div>
  ),
);

DragOverlay.displayName = 'DragOverlay';

export default DragOverlay;
