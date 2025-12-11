// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { Tooltip, useDisclosure } from '@heroui/react';
import React, { useCallback, useMemo, useState } from 'react';

import { useTranslation } from 'next-i18next';

import { FilterComponentType } from '@/types/enums/filters';
import { ProjectStatus } from '@/types/enums/projects';
import { ProjectStorageStatus } from '@/types/enums/storages';
import { ClientSideDataFilter, FilterValueMap } from '@/types/filters';
import { ProjectWithMembers } from '@/types/projects';
import {
  ProjectStoragesResponse,
  ProjectStorageWithParentStorage,
  Storage,
} from '@/types/storages';

import ActionsToolbar from '@/components/shared/Toolbar/ActionsToolbar';

import { AssignStorageToProject, DeleteStorageModal } from '../storages';
import AssignStorageButton from '../storages/AssignStorageButton';
import ProjectStoragesTable from './ProjectStoragesTable';
import { useQuery } from '@tanstack/react-query';
import { fetchProjectStorages } from '@/services/app/storages';
import { doesProjectStorageDataNeedToBeRefreshed } from '@/utils/app/storages';
import { DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA } from '@/utils/app/api-helpers';
import StatusError from '@/components/shared/StatusError/StatusError';
import Status, { StatusProps } from '@/components/shared/Status/Status';
import getProjectStatusVariants from '@/utils/app/projects-status-variants';

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

  const {
    data: projectStoragesData,
    isLoading: isStoragesLoading,
    refetch: refetchProjectStorages,
  } = useQuery<ProjectStoragesResponse>({
    queryKey: ['project-storages', project.id],
    queryFn: () => fetchProjectStorages(project.id),
    initialData: {
      projectStorages,
    },
    refetchInterval: (query) => {
      return !query.state.data ||
        doesProjectStorageDataNeedToBeRefreshed(
          query.state.data.projectStorages,
        )
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
    return projectStoragesData.projectStorages.map((ps) => ps.storage.id);
  }, [projectStoragesData.projectStorages]);

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
        }
      />
      <ProjectStoragesTable
        projectStorages={projectStoragesData.projectStorages}
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
