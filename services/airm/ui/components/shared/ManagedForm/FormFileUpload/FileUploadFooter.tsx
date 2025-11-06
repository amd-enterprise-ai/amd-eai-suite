// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

/**
 * Footer component that shows when files are selected
 */
import { Divider } from '@heroui/react';
import { IconPlus, IconUpload } from '@tabler/icons-react';
import { memo } from 'react';

import type { TFunction } from 'next-i18next';

import { displayBytesInOptimalUnit } from '@/utils/app/memory';
import { ActionButton } from '@/components/shared/Buttons';
import { getTotalFileSizeInBytes } from './utils';

const FileUploadFooter = memo(
  ({
    multiple,
    files,
    onAddFiles,
    t,
  }: {
    multiple: boolean;
    files: File[];
    onAddFiles: () => void;
    t: TFunction;
  }) => {
    const filesCount = files.length;
    const totalSize = getTotalFileSizeInBytes(files);

    return (
      <div className="flex w-full items-center gap-2 justify-between">
        <ActionButton
          tertiary
          size="sm"
          icon={multiple ? <IconPlus size={14} /> : <IconUpload size={14} />}
          onPress={onAddFiles}
          className="rounded"
        >
          {t('add', { count: +multiple + 1 })}
        </ActionButton>
        <div className="flex gap-2 text-sm text-default-500 items-center justify-end mr-2 h-5">
          <span>{t('footerFiles', { count: filesCount })}</span>
          <Divider orientation="vertical" />
          <span>{displayBytesInOptimalUnit(totalSize)}</span>
        </div>
      </div>
    );
  },
);

FileUploadFooter.displayName = 'FileUploadFooter';

export default FileUploadFooter;
