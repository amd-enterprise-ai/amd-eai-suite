// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

/**
 * Empty file upload component that shows when no files are selected
 */
import { Button } from '@heroui/react';
import { IconUpload } from '@tabler/icons-react';
import { memo } from 'react';

import type { TFunction } from 'next-i18next';

const EmptyFileUpload = memo(
  ({
    placeholder,
    multiple,
    onUpload,
    t,
  }: {
    placeholder?: string;
    multiple: boolean;
    onUpload: () => void;
    t: TFunction;
  }) => (
    <Button
      variant="light"
      onPress={onUpload}
      className="h-auto w-full rounded"
    >
      <div className="w-full flex flex-col p-4 gap-2 justify-center items-center text-center text-wrap">
        <IconUpload size={24} className="text-inherit" />
        <p className="text-sm">{placeholder}</p>
        <span className="text-sm opacity-30">
          {t('drop', { count: +multiple + 1 })}
        </span>
      </div>
    </Button>
  ),
);

EmptyFileUpload.displayName = 'EmptyFileUpload';

export default EmptyFileUpload;
