// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { Tooltip, useDisclosure } from '@heroui/react';
import React, { useCallback, useMemo, useState } from 'react';

import { useTranslation } from 'next-i18next';
import { useAccessControl } from '@/hooks/useAccessControl';

import { FilterComponentType } from '@amdenterpriseai/types';
import { ProjectStatus } from '@amdenterpriseai/types';
import { ProjectStorageStatus } from '@amdenterpriseai/types';
import { ClientSideDataFilter, FilterValueMap } from '@amdenterpriseai/types';
import { ProjectWithMembers } from '@amdenterpriseai/types';
import {
  ProjectStoragesResponse,
  ProjectStorageWithParentStorage,
  Storage,
} from '@amdenterpriseai/types';

import { ActionsToolbar } from '@amdenterpriseai/components';

import { AssignStorageToProject, DeleteStorageModal } from '../storages';
import AssignStorageButton from '../storages/AssignStorageButton';
import ProjectStoragesTable from './ProjectStoragesTable';
import { useQuery } from '@tanstack/react-query';
import { fetchProjectStorages } from '@/services/app';
import { doesProjectStorageDataNeedToBeRefreshed } from '@amdenterpriseai/utils/app';
import { DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA } from '@amdenterpriseai/utils/app';
import { StatusError } from '@amdenterpriseai/components';
import { Status, StatusProps } from '@amdenterpriseai/components';
import { getProjectStatusVariants } from '@amdenterpriseai/utils/app';

interface Props {
  project: ProjectWithMembers;
  storages: Storage[];
  projectStorages: ProjectStorageWithParentStorage[];
}

export const ProjectStorages: React.FC<Props> = ({
  project,
  storages,
  projectStorages,
}) => {
  const { t } = useTranslation('storages');
  const { t: tProjects } = useTranslation('projects');
  const { isAdministrator } = useAccessControl();

  const {
    data: projectStoragesData,
    isLoading: isStoragesLoading,
    refetch: refetchProjectStorages,
  } = useQuery<ProjectStoragesResponse>({
    queryKey: ['project-storages', project.id],
    queryFn: () => fetchProjectStorages(project.id),
    initialData: {
      data: projectStorages,
    },
    refetchInterval: (query) => {
      return !query.state.data ||
        doesProjectStorageDataNeedToBeRefreshed(query.state.data.data)
        ? DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA
        : false;
    },
  });

  const [filters, setFilters] = useState<
    ClientSideDataFilter<ProjectStorageWithParentStorage>[]
  >([]);

  const {
    isOpen: isAssignStorageFormOpen,
    onOpenChange: onAssignStorageFormOpenChange,
  } = useDisclosure();

  const [targetStorage, setTargetStorage] =
    useState<ProjectStorageWithParentStorage | null>(null);

  const {
    isOpen: isDeleteStorageOpen,
    onOpenChange: onDeleteStorageOpenChange,
  } = useDisclosure();

  const actions = useMemo(() => {
    return [
      {
        key: 'delete',
        className: 'text-danger',
        color: 'danger',
        onPress: (ps: ProjectStorageWithParentStorage) => {
          setTargetStorage(ps);
          onDeleteStorageOpenChange();
        },
        label: t('list.actions.deleteFromProject.label'),
        isDisabled: (projectStorage: ProjectStorageWithParentStorage) => {
          return projectStorage.status === ProjectStorageStatus.DELETING;
        },
      },
    ];
  }, [t, onDeleteStorageOpenChange]);

  const handleFilterChange = useCallback((filters: FilterValueMap) => {
    const newFilters: ClientSideDataFilter<ProjectStorageWithParentStorage>[] =
      [];
    if (
      filters?.search &&
      filters.search.length > 0 &&
      !(filters.search.length === 1 && filters.search[0] === '')
    ) {
      newFilters.push({
        field: 'storage',
        path: 'name',
        values: filters.search,
      });
    }
    if (filters?.type && filters.type.length > 0) {
      newFilters.push({
        field: 'storage',
        path: 'type',
        values: filters.type,
      });
    }
    setFilters(newFilters);
  }, []);

  const projectCanAddStorage = useMemo(() => {
    return project?.status === ProjectStatus.READY;
  }, [project?.status]);

  const existingStorageIds = useMemo(() => {
    return projectStoragesData.data.map((ps) => ps.storage.id);
  }, [projectStoragesData.data]);

  const filterConfig = {
    search: {
      name: 'search',
      label: t('list.filter.search.label'),
      placeholder: t('list.filter.search.placeholder'),
      type: FilterComponentType.TEXT,
    },
  };

  return (
    <div className="flex flex-col">
      <h3>{t('title')}</h3>
      <ActionsToolbar
        filterConfig={filterConfig}
        onRefresh={refetchProjectStorages}
        onFilterChange={handleFilterChange}
        endContent={
          isAdministrator ? (
            <Tooltip
              content={
                <div className="flex flex-col gap-1">
                  <span>{t('actions.assignProjectStorage.disabled')}</span>
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
              isDisabled={projectCanAddStorage}
            >
              <span>
                <AssignStorageButton
                  onAssignS3Storage={onAssignStorageFormOpenChange}
                  disabled={!projectCanAddStorage}
                />
              </span>
            </Tooltip>
          ) : undefined
        }
      />
      <ProjectStoragesTable
        projectStorages={projectStoragesData.data}
        filters={filters}
        actions={actions}
        isLoading={isStoragesLoading}
      />
      <AssignStorageToProject
        isOpen={isAssignStorageFormOpen}
        onClose={onAssignStorageFormOpenChange}
        project={project}
        storages={storages}
        existingStorageIds={existingStorageIds}
      />
      {targetStorage ? (
        <DeleteStorageModal
          isOpen={isDeleteStorageOpen}
          onOpenChange={onDeleteStorageOpenChange}
          storage={targetStorage.storage}
          projectId={project.id}
        />
      ) : null}
    </div>
  );
};

export default ProjectStorages;
