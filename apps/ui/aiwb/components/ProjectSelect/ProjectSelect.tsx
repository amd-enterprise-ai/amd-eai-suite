// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Select, SelectItem, Tooltip } from '@heroui/react';
import { IconCheckupList } from '@tabler/icons-react';
import { ReactNode, useCallback } from 'react';

import { useTranslation } from 'next-i18next';

import { useProject } from '@/contexts/ProjectContext';

interface Props {
  disabled?: boolean;
  size?: 'sm' | 'md' | 'lg';
  startContent?: ReactNode;
  showTooltip?: boolean;
}

export const ProjectSelect = ({
  disabled = false,
  size,
  startContent,
  showTooltip = true,
}: Props) => {
  const { t } = useTranslation('common');
  const { isStandaloneMode, activeProject, projects, setActiveProject } =
    useProject();

  const onActiveProjectChange = useCallback(
    (projectId: string): void => {
      setActiveProject(projectId);
    },
    [setActiveProject],
  );

  return !isStandaloneMode ? (
    <Tooltip
      content={t('projectSelection.tooltip') || ''}
      placement="bottom"
      isDisabled={!showTooltip}
    >
      <Select
        className="select-wrapper min-w-48"
        data-testid="project-select"
        aria-label={t('projectSelection.label') || ''}
        placeholder={t('projectSelection.placeholder') || ''}
        disallowEmptySelection={true}
        selectedKeys={activeProject ? [activeProject] : []}
        onChange={(e) => onActiveProjectChange(e.target.value)}
        isDisabled={projects.length === 0 || disabled}
        size={size || 'sm'}
        startContent={startContent || <IconCheckupList />}
      >
        {projects.map((project) => (
          <SelectItem
            aria-roledescription="option"
            key={project.id}
            aria-label={project.id}
          >
            {project.name}
          </SelectItem>
        ))}
      </Select>
    </Tooltip>
  ) : null;
};

ProjectSelect.displayName = 'ProjectSelect';
