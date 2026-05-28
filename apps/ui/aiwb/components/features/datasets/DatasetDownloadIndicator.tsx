// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { IconCheck, IconLoader2, IconX } from '@tabler/icons-react';
import { useTranslation } from 'next-i18next';

export enum DownloadStatus {
  PREPARING = 'preparing',
  DONE = 'done',
}

interface DatasetDownloadIndicatorProps {
  status: DownloadStatus;
  onDismiss: () => void;
}

export const DatasetDownloadIndicator: React.FC<
  DatasetDownloadIndicatorProps
> = ({ status, onDismiss }) => {
  const { t } = useTranslation('datasets');

  return (
    <div className="fixed bottom-6 right-6 z-50 flex items-center gap-4 bg-content1 shadow-lg rounded-md px-5 py-4 border border-divider w-full max-w-[360px]">
      {status === DownloadStatus.PREPARING ? (
        <div className="shrink-0 flex items-center justify-center w-12 h-12 rounded-full bg-primary">
          <IconLoader2 className="animate-spin text-white" size={24} />
        </div>
      ) : (
        <div className="shrink-0 flex items-center justify-center w-12 h-12 rounded-full bg-success">
          <IconCheck className="text-white" size={24} />
        </div>
      )}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-bold text-foreground">
          {status === DownloadStatus.PREPARING
            ? t('download.indicator.preparing.title')
            : t('download.indicator.done.title')}
        </p>
        <p className="text-xs text-foreground-500 mt-0.5">
          {status === DownloadStatus.PREPARING
            ? t('download.indicator.preparing.subtitle')
            : t('download.indicator.done.subtitle')}
        </p>
      </div>
      <button
        type="button"
        onClick={onDismiss}
        className="self-start shrink-0 text-foreground-400 hover:text-foreground transition-colors"
        aria-label={t('download.indicator.dismiss')}
      >
        <IconX size={16} />
      </button>
    </div>
  );
};
