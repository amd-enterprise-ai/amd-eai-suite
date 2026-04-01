// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Tooltip, useDisclosure } from '@heroui/react';
import React, { useCallback, useMemo, useState } from 'react';

import { useTranslation } from 'next-i18next';
import { useAccessControl } from '@/hooks/useAccessControl';

import { ProjectStatus, SecretScope } from '@amdenterpriseai/types';
import { ClientSideDataFilter, FilterValueMap } from '@amdenterpriseai/types';
import { ProjectWithMembers } from '@amdenterpriseai/types';
import { ProjectStorage } from '@amdenterpriseai/types';
import {
  ProjectSecretsResponse,
  ProjectSecretWithParentSecret,
  Secret,
} from '@amdenterpriseai/types';
import { FilterComponentType } from '@amdenterpriseai/types';
import { SecretType } from '@amdenterpriseai/types';

import { AddSecret, AssignOrgSecretToProject } from '../secrets';
import DeleteSecretModal from '../secrets/DeleteSecretModal';
import ProjectSecretsTable from './ProjectSecretsTable';
import { ActionsToolbar } from '@amdenterpriseai/components';
import AddProjectSecretButton from '../secrets/AddProjectSecretButton';
import { useQuery } from '@tanstack/react-query';
import { fetchProjectSecrets } from '@/services/app';
import { doesProjectSecretDataNeedToBeRefreshed } from '@amdenterpriseai/utils/app';
import { DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA } from '@amdenterpriseai/utils/app';
import { Status, StatusProps } from '@amdenterpriseai/components';
import { getProjectStatusVariants } from '@amdenterpriseai/utils/app';
import { StatusError } from '@amdenterpriseai/components';

interface Props {
  project: ProjectWithMembers;
  secrets: Secret[];
  projectSecrets: ProjectSecretWithParentSecret[];
  projectStorages: ProjectStorage[];
}

export const ProjectSecrets: React.FC<Props> = ({
  project,
  secrets,
  projectSecrets,
  projectStorages,
}) => {
  const { t } = useTranslation('secrets');
  const { t: tProjects } = useTranslation('projects');
  const { isAdministrator } = useAccessControl();

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

  const {
    data: projectSecretsData,
    isLoading: isSecretsLoading,
    refetch: refetchSecrets,
  } = useQuery<ProjectSecretsResponse>({
    queryKey: ['secrets', project.id],
    queryFn: () => fetchProjectSecrets(project.id),
    initialData: {
      data: projectSecrets,
    },
    refetchInterval: (query) => {
      return !query.state.data ||
        doesProjectSecretDataNeedToBeRefreshed(query.state.data.data)
        ? DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA
        : false;
    },
  });

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
          const isUsedByStorage = projectStorages.some(
            (ps) => ps.storage.secretId === projectSecret.secret.id,
          );

          return isUsedByStorage;
        },
      },
    ];
  }, [t, onDeleteSecretOpenChange, projectStorages]);

  const handleFilterChange = useCallback((filters: FilterValueMap) => {
    const newFilters: ClientSideDataFilter<ProjectSecretWithParentSecret>[] =
      [];
    if (
      filters?.search &&
      filters.search.length > 0 &&
      !(filters.search.length === 1 && filters.search[0] === '')
    ) {
      newFilters.push({
        field: 'secret',
        path: 'name',
        values: filters.search,
      });
    }
    if (filters?.type && filters.type.length > 0) {
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
        onRefresh={refetchSecrets}
        onFilterChange={handleFilterChange}
        endContent={
          <Tooltip
            content={
              <div className="flex flex-col gap-1">
                <span>{t('actions.addProjectSecret.disabled')}</span>
                <Status
                  {...(getProjectStatusVariants(tProjects)[
                    project.status
                  ] as StatusProps)}
                  isClickable
                  helpContent={
                    project.statusReason ? (
                      <StatusError statusReason={project.statusReason} />
                    ) : undefined
                  }
                />
              </div>
            }
            isDisabled={projectCanAddSecret}
          >
            <span>
              <AddProjectSecretButton
                disabled={!projectCanAddSecret}
                onOpenProjectSecret={onAddSecretFormOpenChange}
                onOpenProjectAssignment={onAssignSecretFormOpenChange}
              />
            </span>
          </Tooltip>
        }
      />
      <ProjectSecretsTable
        projectSecrets={projectSecretsData.data}
        filters={filters}
        actions={actions}
        isLoading={isSecretsLoading}
      />
      <AddSecret
        isOpen={isAddSecretFormOpen}
        projects={[project]}
        onCreateSuccess={refetchSecrets}
        onClose={onAddSecretFormOpenChange}
        secrets={secrets}
        defaultScope={SecretScope.PROJECT}
        scopeSelectDisabled={true}
        projectSelectDisabled={true}
      />
      {isAdministrator && (
        <AssignOrgSecretToProject
          project={project}
          isOpen={isAssignSecretFormOpen}
          onClose={onAssignSecretFormOpenChange}
        />
      )}
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
