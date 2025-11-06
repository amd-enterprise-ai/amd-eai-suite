// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Tooltip, useDisclosure } from '@heroui/react';
import { IconAlertTriangle } from '@tabler/icons-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback, useState } from 'react';

import { Trans, useTranslation } from 'next-i18next';
import router from 'next/router';

import useSystemToast from '@/hooks/useSystemToast';

import { deleteProject as deleteProjectAPI } from '@/services/app/projects';

import { APIRequestError } from '@/utils/app/errors';
import {
  formatGpuAllocation,
  formatCpuAllocation,
  formatMemoryAllocation,
} from '@/utils/app/strings';

import { TableColumns } from '@/types/data-table/clientside-table';
import { CustomComparatorConfig } from '@/types/data-table/table-comparators';
import { ProjectTableField } from '@/types/enums/project-table-fields';
import { ProjectWithResourceAllocation } from '@/types/projects';

import { ConfirmationModal } from '@/components/shared/Confirmation/ConfirmationModal';
import ClientSideDataTable from '@/components/shared/DataTable/ClientSideDataTable';

import { ProjectStatusField } from './ProjectStatusField';

interface Props {
  projects: ProjectWithResourceAllocation[];
}

const customComparator: CustomComparatorConfig<
  ProjectWithResourceAllocation,
  ProjectTableField
> = {
  [ProjectTableField.GPU_ALLOCATION]: (
    a: ProjectWithResourceAllocation,
    b: ProjectWithResourceAllocation,
  ): number => {
    return a.quota.gpuCount - b.quota.gpuCount;
  },
  [ProjectTableField.CPU_ALLOCATION]: (
    a: ProjectWithResourceAllocation,
    b: ProjectWithResourceAllocation,
  ): number => {
    return a.quota.cpuMilliCores - b.quota.cpuMilliCores;
  },
  [ProjectTableField.MEMORY_ALLOCATION]: (
    a: ProjectWithResourceAllocation,
    b: ProjectWithResourceAllocation,
  ): number => {
    return a.quota.memoryBytes - b.quota.memoryBytes;
  },
};

export const ProjectTable: React.FC<Props> = ({ projects }) => {
  const { t } = useTranslation('projects');

  const columns: TableColumns<ProjectTableField | null> = [
    { key: ProjectTableField.NAME, sortable: true },
    { key: ProjectTableField.STATUS, sortable: true },
    { key: ProjectTableField.GPU_ALLOCATION, sortable: true },
    { key: ProjectTableField.CPU_ALLOCATION, sortable: true },
    { key: ProjectTableField.MEMORY_ALLOCATION, sortable: true },
  ];
  const [targetProject, setTargetProject] =
    useState<ProjectWithResourceAllocation | null>(null);

  const actions = [
    {
      key: 'edit',
      onPress: (p: ProjectWithResourceAllocation) => {
        router.push(`/projects/${p.id}`);
      },
      label: t('list.projects.actions.edit.label'),
    },
    {
      key: 'delete',
      className: 'text-danger',
      color: 'danger',
      onPress: (p: ProjectWithResourceAllocation) => {
        setTargetProject(p);
        onDeleteModalOpen();
      },
      label: t('list.projects.actions.delete.label'),
    },
  ];

  const customRenderers: Partial<
    Record<
      ProjectTableField,
      (item: ProjectWithResourceAllocation) => React.ReactNode | string
    >
  > = {
    [ProjectTableField.STATUS]: (item) => (
      <ProjectStatusField
        status={item.status}
        statusReason={item.statusReason}
      />
    ),
    [ProjectTableField.NAME]: (item) => item.name,
    [ProjectTableField.GPU_ALLOCATION]: (
      item: ProjectWithResourceAllocation,
    ) => {
      const allocation = formatGpuAllocation(
        item.quota.gpuCount,
        item.gpuAllocationPercentage,
      );

      if (item.gpuAllocationExceeded) {
        return (
          <div className="flex items-center gap-2">
            {allocation}
            <Tooltip content={t('list.projects.warnings.gpuWarning')}>
              <IconAlertTriangle size={16} className={'stroke-warning-500'} />
            </Tooltip>
          </div>
        );
      }

      return allocation;
    },
    [ProjectTableField.CPU_ALLOCATION]: (
      item: ProjectWithResourceAllocation,
    ) => {
      const allocation = formatCpuAllocation(
        item.quota.cpuMilliCores,
        item.cpuAllocationPercentage,
      );

      if (item.cpuAllocationExceeded) {
        return (
          <div className="flex items-center gap-2">
            {allocation}
            <Tooltip content={t('list.projects.warnings.cpuWarning')}>
              <IconAlertTriangle size={16} className={'stroke-warning-500'} />
            </Tooltip>
          </div>
        );
      }

      return allocation;
    },
    [ProjectTableField.MEMORY_ALLOCATION]: (
      item: ProjectWithResourceAllocation,
    ) => {
      const allocation = formatMemoryAllocation(
        item.quota.memoryBytes,
        item.memoryAllocationPercentage,
      );

      if (item.memoryAllocationExceeded) {
        return (
          <div className="flex items-center gap-2">
            {allocation}
            <Tooltip content={t('list.projects.warnings.memoryWarning')}>
              <IconAlertTriangle size={16} className={'stroke-warning-500'} />
            </Tooltip>
          </div>
        );
      }

      return allocation;
    },
  };

  const {
    isOpen: isDeleteModalOpen,
    onOpen: onDeleteModalOpen,
    onOpenChange: onDeleteModalOpenChange,
  } = useDisclosure();
  const queryClient = useQueryClient();
  const { toast } = useSystemToast();

  const { mutate: deleteProject, isPending: isDeletePending } = useMutation({
    mutationFn: deleteProjectAPI,
    onSuccess: () => {
      onDeleteModalOpenChange();
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['cluster', 'projects'] });
      toast.success(t('settings.delete.notification.success'));
    },
    onError: (error) => {
      toast.error(
        t('settings.delete.notification.error'),
        error as APIRequestError,
      );
      console.error('Error deleting project:', error);
      onDeleteModalOpenChange();
    },
  });

  const handleRowPressed = (id: string) => {
    router.push(`/projects/${id}`);
  };

  const handleDelete = useCallback(() => {
    if (targetProject) {
      deleteProject(targetProject.id);
    }
  }, [targetProject, deleteProject]);

  return (
    <>
      <ClientSideDataTable
        data={projects}
        columns={columns}
        defaultSortByField={ProjectTableField.NAME}
        translation={t}
        idKey="id"
        customRenderers={customRenderers}
        customComparator={customComparator}
        rowActions={actions}
        translationKeyPrefix="projects"
        onRowPressed={handleRowPressed}
        className="overflow-y-auto"
      />
      <ConfirmationModal
        confirmationButtonColor="danger"
        description={
          <Trans parent="span">
            {t('settings.delete.confirmation.description', {
              project: targetProject?.name,
            })}
          </Trans>
        }
        title={t('settings.delete.confirmation.title')}
        isOpen={isDeleteModalOpen}
        loading={isDeletePending}
        onConfirm={handleDelete}
        onClose={onDeleteModalOpenChange}
      />
    </>
  );
};

export default ProjectTable;
