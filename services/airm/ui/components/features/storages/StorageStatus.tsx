// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  IconCircleCheckFilled,
  IconCircleXFilled,
  IconLineDashed,
  IconLoaderQuarter,
} from '@tabler/icons-react';
import { JSX, useMemo } from 'react';

import { StorageStatus as StorageStatusEnum } from '@/types/enums/storages';
import { SecondaryStatusReason } from '@/types/status-error-popover';

import { BaseStatusDisplay } from '@/components/shared/Status';

interface Props {
  status: StorageStatusEnum;
  statusReason: string | null;
  secondaryStatusReason?: SecondaryStatusReason[];
}

const statusIcons: Record<StorageStatusEnum, JSX.Element | null> = {
  [StorageStatusEnum.PENDING]: (
    <IconLoaderQuarter
      className="stroke-warning-400 animate-spin"
      aria-label={StorageStatusEnum.PENDING}
    />
  ),
  [StorageStatusEnum.PARTIALLY_SYNCED]: (
    <IconLoaderQuarter
      className="stroke-warning-400 animate-spin"
      aria-label={StorageStatusEnum.PARTIALLY_SYNCED}
    />
  ),
  [StorageStatusEnum.UNASSIGNED]: (
    <IconLineDashed aria-label={StorageStatusEnum.UNASSIGNED} />
  ),
  [StorageStatusEnum.SYNCED]: (
    <IconCircleCheckFilled
      className="fill-success-400"
      aria-label={StorageStatusEnum.SYNCED}
    />
  ),
  [StorageStatusEnum.SYNCED_ERROR]: (
    <IconCircleXFilled
      className="fill-danger-400"
      aria-label={StorageStatusEnum.SYNCED_ERROR}
    />
  ),
  [StorageStatusEnum.FAILED]: (
    <IconCircleXFilled
      className="fill-danger-400"
      aria-label={StorageStatusEnum.FAILED}
    />
  ),
  [StorageStatusEnum.DELETING]: (
    <IconLoaderQuarter
      className="stroke-warning-400 animate-spin"
      aria-label={StorageStatusEnum.DELETING}
    />
  ),
  [StorageStatusEnum.DELETED]: (
    <IconCircleXFilled
      className="fill-danger-400"
      aria-label={StorageStatusEnum.DELETED}
    />
  ),
  [StorageStatusEnum.DELETE_FAILED]: (
    <IconCircleXFilled
      className="fill-danger-400"
      aria-label={StorageStatusEnum.DELETE_FAILED}
    />
  ),
};

export const StorageStatus: React.FC<Props> = ({
  status,
  statusReason,
  secondaryStatusReason,
}) => {
  const hasError = useMemo(
    () =>
      status === StorageStatusEnum.FAILED ||
      status === StorageStatusEnum.DELETE_FAILED ||
      status === StorageStatusEnum.SYNCED_ERROR,
    [status],
  );

  return (
    <BaseStatusDisplay
      status={status}
      statusPrefix="storageStatus"
      translationNamespace="storages"
      statusReason={statusReason}
      secondaryStatusReason={secondaryStatusReason}
      statusIconMap={statusIcons}
      statusesToHide={[StorageStatusEnum.UNASSIGNED]}
      hasErrors={hasError}
    />
  );
};

export default StorageStatus;
