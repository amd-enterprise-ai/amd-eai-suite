// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

/**
 * File element component that shows file in the list
 */
import { IconFile, IconX } from '@tabler/icons-react';
import { memo } from 'react';

import type { TFunction } from 'next-i18next';
import { ActionButton } from '@/components/shared/Buttons';
import { displayBytesInOptimalUnit } from '@/utils/app/memory';

const FileElement = memo(
  ({
    file,
    onRemove,
    t,
  }: {
    file: File;
    onRemove: () => void;
    t: TFunction;
  }) => (
    <div className="flex items-center gap-1 rounded p-1 pl-2 bg-default-100">
      <IconFile size={16} />
      <span className="text-sm truncate w-full">{file.name}</span>
      <span className="text-sm text-default-500/50 text-nowrap">
        {displayBytesInOptimalUnit(file.size)}
      </span>
      <ActionButton
        tertiary
        size="sm"
        className="rounded"
        aria-label={t('remove')}
        onPress={onRemove}
        icon={<IconX size={16} />}
      />
    </div>
  ),
);

FileElement.displayName = 'FileElement';

export default FileElement;
