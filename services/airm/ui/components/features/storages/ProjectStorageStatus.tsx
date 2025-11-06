// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import {
  IconCircleCheckFilled,
  IconCircleXFilled,
  IconLoaderQuarter,
} from '@tabler/icons-react';
import { JSX, useMemo } from 'react';

import { ProjectStorageStatus as ProjectStorageStatusEnum } from '@/types/enums/storages';

import { BaseStatusDisplay } from '@/components/shared/Status';

interface Props {
  status: ProjectStorageStatusEnum;
  statusReason: string | null;
}

const statusIcons: Record<ProjectStorageStatusEnum, JSX.Element | null> = {
  [ProjectStorageStatusEnum.PENDING]: (
    <IconLoaderQuarter
      className="stroke-warning-400 animate-spin"
      aria-label={ProjectStorageStatusEnum.PENDING}
    />
  ),
  [ProjectStorageStatusEnum.SYNCED]: (
    <IconCircleCheckFilled
      className="fill-success-400"
      aria-label={ProjectStorageStatusEnum.SYNCED}
    />
  ),
  [ProjectStorageStatusEnum.SYNCED_ERROR]: (
    <IconCircleXFilled
      className="fill-danger-400"
      aria-label={ProjectStorageStatusEnum.SYNCED_ERROR}
    />
  ),
  [ProjectStorageStatusEnum.FAILED]: (
    <IconCircleXFilled
      className="fill-danger-400"
      aria-label={ProjectStorageStatusEnum.FAILED}
    />
  ),
  [ProjectStorageStatusEnum.DELETING]: (
    <IconLoaderQuarter
      className="stroke-warning-400 animate-spin"
      aria-label={ProjectStorageStatusEnum.DELETING}
    />
  ),
  [ProjectStorageStatusEnum.DELETED]: (
    <IconCircleXFilled
      className="fill-danger-400"
      aria-label={ProjectStorageStatusEnum.DELETED}
    />
  ),
  [ProjectStorageStatusEnum.DELETE_FAILED]: (
    <IconCircleXFilled
      className="fill-danger-400"
      aria-label={ProjectStorageStatusEnum.DELETE_FAILED}
    />
  ),
};

export const ProjectStorageStatus: React.FC<Props> = ({
  status,
  statusReason,
}) => {
  const hasError = useMemo(
    () =>
      status === ProjectStorageStatusEnum.FAILED ||
      status === ProjectStorageStatusEnum.DELETE_FAILED ||
      status === ProjectStorageStatusEnum.SYNCED_ERROR,
    [status],
  );

  return (
    <BaseStatusDisplay
      status={status}
      translationNamespace="storages"
      statusPrefix="storageStatus"
      statusReason={statusReason}
      statusIconMap={statusIcons}
      hasErrors={hasError}
    />
  );
};
