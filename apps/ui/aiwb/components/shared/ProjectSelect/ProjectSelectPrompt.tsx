// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { IconCheckupList } from '@tabler/icons-react';
import { useTranslation } from 'next-i18next';
import { HeroMessage } from '@amdenterpriseai/components';
import { ErrorCodes, Intent } from '@amdenterpriseai/types';
import { ProjectSelect } from './ProjectSelect';

interface ProjectSelectPromptProps {
  errorCode?: string;
}

export function ProjectSelectPrompt({ errorCode }: ProjectSelectPromptProps) {
  const { t } = useTranslation('common');

  const isError =
    errorCode && Object.values(ErrorCodes).includes(errorCode as ErrorCodes);

  return (
    <HeroMessage
      intent={isError ? Intent.DANGER : undefined}
      icon={IconCheckupList}
      title={
        isError ? t(`error.${errorCode}.title`) : t('projectSelectPrompt.title')
      }
      description={
        isError
          ? t(`error.${errorCode}.description`)
          : t('projectSelectPrompt.description')
      }
      endContent={<ProjectSelect size="md" showTooltip={false} />}
    />
  );
}
