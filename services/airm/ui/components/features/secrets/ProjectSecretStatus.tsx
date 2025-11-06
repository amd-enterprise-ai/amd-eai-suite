// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  IconCircleCheckFilled,
  IconCircleXFilled,
  IconLoaderQuarter,
} from '@tabler/icons-react';
import { JSX, useMemo } from 'react';

import { ProjectSecretStatus as ProjectSecretStatusEnum } from '@/types/enums/secrets';

import { BaseStatusDisplay } from '@/components/shared/Status';

interface Props {
  status: ProjectSecretStatusEnum;
  statusReason: string | null;
}

const statusIcons: Record<ProjectSecretStatusEnum, JSX.Element | null> = {
  [ProjectSecretStatusEnum.PENDING]: (
    <IconLoaderQuarter
      className="stroke-warning-400 animate-spin"
      aria-label={ProjectSecretStatusEnum.PENDING}
    />
  ),
  [ProjectSecretStatusEnum.SYNCED]: (
    <IconCircleCheckFilled
      className="fill-success-400"
      aria-label={ProjectSecretStatusEnum.SYNCED}
    />
  ),
  [ProjectSecretStatusEnum.SYNCED_ERROR]: (
    <IconCircleXFilled
      className="fill-danger-400"
      aria-label={ProjectSecretStatusEnum.SYNCED_ERROR}
    />
  ),
  [ProjectSecretStatusEnum.FAILED]: (
    <IconCircleXFilled
      className="fill-danger-400"
      aria-label={ProjectSecretStatusEnum.FAILED}
    />
  ),
  [ProjectSecretStatusEnum.DELETING]: (
    <IconLoaderQuarter
      className="stroke-warning-400 animate-spin"
      aria-label={ProjectSecretStatusEnum.DELETING}
    />
  ),
  [ProjectSecretStatusEnum.DELETED]: (
    <IconCircleXFilled
      className="fill-danger-400"
      aria-label={ProjectSecretStatusEnum.DELETED}
    />
  ),
  [ProjectSecretStatusEnum.DELETE_FAILED]: (
    <IconCircleXFilled
      className="fill-danger-400"
      aria-label={ProjectSecretStatusEnum.DELETE_FAILED}
    />
  ),
};

export const ProjectSecretStatus: React.FC<Props> = ({
  status,
  statusReason,
}) => {
  const hasError = useMemo(
    () =>
      status === ProjectSecretStatusEnum.FAILED ||
      status === ProjectSecretStatusEnum.DELETE_FAILED ||
      status === ProjectSecretStatusEnum.SYNCED_ERROR,
    [status],
  );

  return (
    <BaseStatusDisplay
      status={status}
      translationNamespace="secrets"
      statusPrefix="secretStatus"
      statusReason={statusReason}
      statusIconMap={statusIcons}
      hasErrors={hasError}
    />
  );
};
