// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { Tooltip, useDisclosure } from '@heroui/react';
import React, { useCallback, useMemo, useState } from 'react';

import { useTranslation } from 'next-i18next';

import { FilterComponentType } from '@/types/enums/filters';
import { ProjectStatus } from '@/types/enums/projects';
import { ProjectStorageStatus, StorageType } from '@/types/enums/storages';
import { ClientSideDataFilter, FilterValueMap } from '@/types/filters';
import { ProjectWithMembers } from '@/types/projects';
import { Secret } from '@/types/secrets';
import { ProjectStorageWithParentStorage, Storage } from '@/types/storages';

import ActionsToolbar from '@/components/shared/Toolbar/ActionsToolbar';

import { AddSecret } from '../secrets';
import { AddS3Storage, DeleteStorageModal } from '../storages';
import AddStorageButton from '../storages/AddStorageButton';
import ProjectStatusField from './ProjectStatusField';
import ProjectStoragesTable from './ProjectStoragesTable';

interface Props {
  project: ProjectWithMembers;
  secrets: Secret[];
  storages: Storage[];
  projectStorages: ProjectStorageWithParentStorage[];
}

export const ProjectStorages: React.FC<Props> = ({
  project,
  secrets,
  storages,
  projectStorages,
}) => {
  const { t } = useTranslation('storages');

  const [filters, setFilters] = useState<
    ClientSideDataFilter<ProjectStorageWithParentStorage>[]
  >([]);

  const {
    isOpen: isAddSecretFormOpen,
    onOpenChange: onAddSecretFormOpenChange,
  } = useDisclosure();

  const {
    isOpen: isAdd3StorageFormOpen,
    onOpenChange: onAdd3StorageFormOpenChange,
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
      filters &&
      filters.search &&
      filters.search.length > 0 &&
      !(filters.search.length === 1 && filters.search[0] === '')
    ) {
      newFilters.push({
        field: 'storage',
        path: 'name',
        values: filters.search,
      });
    }
    if (filters && filters.type && filters.type.length > 0) {
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
        onFilterChange={handleFilterChange}
        endContent={
          <Tooltip
            content={
              <div>
                {t('actions.addProjectStorage.disabled')}
                <ProjectStatusField
                  status={project.status}
                  statusReason={project.statusReason}
                />
              </div>
            }
            isDisabled={projectCanAddStorage}
          >
            <span>
              <AddStorageButton
                inProject
                storageTypes={{
                  [StorageType.S3]: onAdd3StorageFormOpenChange,
                }}
                disabled={!projectCanAddStorage}
              />
            </span>
          </Tooltip>
        }
      />
      <ProjectStoragesTable
        projectStorages={projectStorages}
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
      <AddS3Storage
        isOpen={isAdd3StorageFormOpen}
        onClose={onAdd3StorageFormOpenChange}
        project={project}
        secrets={secrets}
        storages={storages}
        openAddSecret={onAddSecretFormOpenChange}
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
