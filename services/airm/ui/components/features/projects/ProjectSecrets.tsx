// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Dropdown,
  DropdownItem,
  DropdownMenu,
  DropdownTrigger,
  Tooltip,
  useDisclosure,
} from '@heroui/react';
import React, { useCallback, useMemo, useState } from 'react';

import { useTranslation } from 'next-i18next';

import { ProjectStatus } from '@/types/enums/projects';
import { ProjectSecretStatus, SecretScope } from '@/types/enums/secrets';
import { ClientSideDataFilter, FilterValueMap } from '@/types/filters';
import { ProjectWithMembers } from '@/types/projects';
import { ProjectSecretWithParentSecret, Secret } from '@/types/secrets';
import { FilterComponentType } from '@/types/enums/filters';
import { SecretType } from '@/types/enums/secrets';

import { AddSecret, AssignSecretToProject } from '../secrets';
import DeleteSecretModal from '../secrets/DeleteSecretModal';
import ProjectSecretsTable from './ProjectSecretsTable';
import ProjectStatusField from './ProjectStatusField';
import { ActionButton } from '@/components/shared/Buttons';
import ActionsToolbar from '@/components/shared/Toolbar/ActionsToolbar';

interface Props {
  project: ProjectWithMembers;
  secrets: Secret[];
  projectSecrets: ProjectSecretWithParentSecret[];
}

export const ProjectSecrets: React.FC<Props> = ({
  project,
  secrets,
  projectSecrets,
}) => {
  const { t } = useTranslation('secrets');

  const [filters, setFilters] = useState<
    ClientSideDataFilter<ProjectSecretWithParentSecret>[]
  >([]);

  const {
    isOpen: isAddSecretFormOpen,
    onOpenChange: onAddSecretFormOpenChange,
  } = useDisclosure();

  const {
    isOpen: isAssignSecretFormOpen,
    onOpenChange: onAssignSecretFormOpenChange,
  } = useDisclosure();

  const [targetSecret, setTargetSecret] =
    useState<ProjectSecretWithParentSecret | null>(null);

  const { isOpen: isDeleteSecretOpen, onOpenChange: onDeleteSecretOpenChange } =
    useDisclosure();

  const actions = useMemo(() => {
    return [
      {
        key: 'delete',
        className: 'text-danger',
        color: 'danger',
        onPress: (ps: ProjectSecretWithParentSecret) => {
          setTargetSecret(ps);
          onDeleteSecretOpenChange();
        },
        label: t('list.actions.delete.projectSecret.label'),
        isDisabled: (projectSecret: ProjectSecretWithParentSecret) => {
          return projectSecret.status === ProjectSecretStatus.DELETING;
        },
      },
    ];
  }, [t, onDeleteSecretOpenChange]);

  const availableSecretsForAssign = useMemo(() => {
    // build a set of names already assigned on the project
    const assignedSecretNames = new Set(
      (projectSecrets ?? [])
        .map((ps) => ps?.secret?.name)
        .filter((n): n is string => Boolean(n)),
    );

    // filter out any secret whose name is already assigned
    return (secrets ?? []).filter(
      (s) =>
        s?.name &&
        !assignedSecretNames.has(s.name) &&
        s.scope === SecretScope.ORGANIZATION &&
        !s.projectSecrets?.some((ps) => ps.projectId === project.id),
    );
  }, [secrets, projectSecrets, project.id]);

  const handleFilterChange = useCallback((filters: FilterValueMap) => {
    const newFilters: ClientSideDataFilter<ProjectSecretWithParentSecret>[] =
      [];
    if (
      filters &&
      filters.search &&
      filters.search.length > 0 &&
      !(filters.search.length === 1 && filters.search[0] === '')
    ) {
      newFilters.push({
        field: 'secret',
        path: 'name',
        values: filters.search,
      });
    }
    if (filters && filters.type && filters.type.length > 0) {
      newFilters.push({
        field: 'secret',
        path: 'type',
        values: filters.type,
      });
    }
    setFilters(newFilters);
  }, []);

  const projectCanAddSecret = useMemo(() => {
    return project?.status === ProjectStatus.READY;
  }, [project?.status]);

  const filterConfig = {
    search: {
      name: 'search',
      label: t('list.filter.search.label'),
      placeholder: t('list.filter.search.placeholder'),
      type: FilterComponentType.TEXT,
    },
    type: {
      name: 'type',
      label: t('list.filter.type.label'),
      placeholder: t('list.filter.type.placeholder'),
      type: FilterComponentType.DROPDOWN,
      fields: Object.values(SecretType).map((type) => ({
        key: type,
        label: t(`list.filter.type.options.${type}`),
      })),
    },
  };

  return (
    <div className="flex flex-col">
      <h3>{t('title')}</h3>
      <ActionsToolbar
        filterConfig={filterConfig}
        onFilterChange={handleFilterChange}
        endContent={
          <Dropdown>
            <Tooltip
              content={
                <div>
                  {t('actions.addProjectSecret.disabled')}
                  <ProjectStatusField
                    status={project.status}
                    statusReason={project.statusReason}
                  />
                </div>
              }
              isDisabled={projectCanAddSecret}
            >
              <span>
                <DropdownTrigger>
                  <ActionButton
                    primary
                    isDisabled={!projectCanAddSecret}
                    aria-label={t('actions.addProjectSecret.label')}
                  >
                    {t('actions.addProjectSecret.label')}
                  </ActionButton>
                </DropdownTrigger>
              </span>
            </Tooltip>

            <DropdownMenu aria-label={t('actions.addProjectSecret.label')}>
              <DropdownItem
                key="add"
                onPress={onAddSecretFormOpenChange}
                aria-label={t('actions.add')}
              >
                {t('actions.add')}
              </DropdownItem>
              <DropdownItem
                key="assign"
                onPress={onAssignSecretFormOpenChange}
                aria-label={t('actions.assign')}
              >
                {t('actions.assign')}
              </DropdownItem>
            </DropdownMenu>
          </Dropdown>
        }
      />
      <ProjectSecretsTable
        projectSecrets={projectSecrets}
        filters={filters}
        actions={actions}
        projectId={project.id}
      />
      <AddSecret
        isOpen={isAddSecretFormOpen}
        projects={[project]}
        onClose={onAddSecretFormOpenChange}
        project={project}
        secrets={secrets}
      />
      <AssignSecretToProject
        isOpen={isAssignSecretFormOpen}
        project={project}
        availableSecrets={availableSecretsForAssign}
        onClose={onAssignSecretFormOpenChange}
      />
      <DeleteSecretModal
        isOpen={isDeleteSecretOpen}
        onOpenChange={onDeleteSecretOpenChange}
        secret={targetSecret?.secret ? targetSecret.secret : null}
        projectId={project.id}
        queryKeyToInvalidate={['secrets', project.id]}
      />
    </div>
  );
};

export default ProjectSecrets;
