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

import { SecretStatus as SecretStatusEnum } from '@/types/enums/secrets';
import { SecondaryStatusReason } from '@/types/status-error-popover';

import { BaseStatusDisplay } from '@/components/shared/Status';

interface Props {
  status: SecretStatusEnum;
  statusReason: string | null;
  secondaryStatusReason?: SecondaryStatusReason[];
}

const statusIcons: Record<SecretStatusEnum, JSX.Element | null> = {
  [SecretStatusEnum.PENDING]: (
    <IconLoaderQuarter
      className="stroke-warning-400 animate-spin"
      aria-label={SecretStatusEnum.PENDING}
    />
  ),
  [SecretStatusEnum.PARTIALLY_SYNCED]: (
    <IconLoaderQuarter
      className="stroke-warning-400 animate-spin"
      aria-label={SecretStatusEnum.PARTIALLY_SYNCED}
    />
  ),
  [SecretStatusEnum.UNASSIGNED]: (
    <IconLineDashed aria-label={SecretStatusEnum.UNASSIGNED} />
  ),
  [SecretStatusEnum.SYNCED]: (
    <IconCircleCheckFilled
      className="fill-success-400"
      aria-label={SecretStatusEnum.SYNCED}
    />
  ),
  [SecretStatusEnum.SYNCED_ERROR]: (
    <IconCircleXFilled
      className="fill-danger-400"
      aria-label={SecretStatusEnum.SYNCED_ERROR}
    />
  ),
  [SecretStatusEnum.FAILED]: (
    <IconCircleXFilled
      className="fill-danger-400"
      aria-label={SecretStatusEnum.FAILED}
    />
  ),
  [SecretStatusEnum.DELETING]: (
    <IconLoaderQuarter
      className="stroke-warning-400 animate-spin"
      aria-label={SecretStatusEnum.DELETING}
    />
  ),
  [SecretStatusEnum.DELETED]: (
    <IconCircleXFilled
      className="fill-danger-400"
      aria-label={SecretStatusEnum.DELETED}
    />
  ),
  [SecretStatusEnum.DELETE_FAILED]: (
    <IconCircleXFilled
      className="fill-danger-400"
      aria-label={SecretStatusEnum.DELETE_FAILED}
    />
  ),
};

export const SecretStatus: React.FC<Props> = ({
  status,
  statusReason,
  secondaryStatusReason,
}) => {
  const hasError = useMemo(
    () =>
      status === SecretStatusEnum.FAILED ||
      status === SecretStatusEnum.DELETE_FAILED ||
      status === SecretStatusEnum.SYNCED_ERROR,
    [status],
  );

  return (
    <BaseStatusDisplay
      status={status}
      statusPrefix="secretStatus"
      translationNamespace="secrets"
      statusReason={statusReason}
      secondaryStatusReason={secondaryStatusReason}
      statusIconMap={statusIcons}
      statusesToHide={[SecretStatusEnum.UNASSIGNED]}
      hasErrors={hasError}
    />
  );
};
