// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  IconCircleCheckFilled,
  IconCircleXFilled,
  IconProgress,
  IconProgressCheck,
} from '@tabler/icons-react';
import React, { ReactNode } from 'react';

import { useTranslation } from 'next-i18next';

import { ProjectStatus } from '@/types/enums/projects';

import StatusErrorPopover from '@/components/shared/StatusErrorPopover/StatusErrorPopover';

interface Props {
  status: ProjectStatus;
  statusReason?: string | null;
}

const translationKey = 'projects';
export const ProjectStatusField: React.FC<Props> = ({
  status,
  statusReason,
}) => {
  const { t } = useTranslation(translationKey);
  let icon: ReactNode = null;

  switch (status) {
    case ProjectStatus.READY:
      icon = (
        <IconCircleCheckFilled
          role="img"
          className="fill-success-500"
          size={16}
        />
      );
      break;
    case ProjectStatus.PARTIALLY_READY:
      icon = (
        <IconProgressCheck
          size={16}
          role="img"
          className="stroke-primary-500"
        />
      );
      break;
    case ProjectStatus.PENDING:
      icon = (
        <IconProgress
          size={16}
          role="img"
          className="stroke-primary-500 animate-spin"
        />
      );
      break;
    case ProjectStatus.DELETING:
      icon = (
        <IconProgress
          size={16}
          role="img"
          className="stroke-primary-500 animate-spin"
        />
      );
      break;
    case ProjectStatus.FAILED:
      icon = (
        <IconCircleXFilled role="img" className="fill-danger-500" size={16} />
      );
      break;
    default:
      return <></>;
  }

  return (
    <div className="flex items-center gap-2">
      {icon}
      <span>{t(`status.${status}`)}</span>
      {status === ProjectStatus.FAILED && !!statusReason && (
        <StatusErrorPopover
          statusReason={statusReason}
          triggerText={t('statusReason.messageTrigger')}
          headerText={t('statusReason.messageHeader')}
        />
      )}
    </div>
  );
};

export default ProjectStatusField;
