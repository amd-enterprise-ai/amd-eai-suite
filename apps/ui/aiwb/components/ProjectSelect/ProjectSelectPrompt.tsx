// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { IconCheckupList } from '@tabler/icons-react';
import { useTranslation } from 'next-i18next';
import { HeroMessage } from '@amdenterpriseai/components';
import { ProjectSelect } from './ProjectSelect';

export function ProjectSelectPrompt() {
  const { t } = useTranslation('common');

  return (
    <HeroMessage
      icon={IconCheckupList}
      title={t('projectSelectPrompt.title')}
      description={t('projectSelectPrompt.description')}
      endContent={<ProjectSelect size="md" showTooltip={false} />}
    />
  );
}
