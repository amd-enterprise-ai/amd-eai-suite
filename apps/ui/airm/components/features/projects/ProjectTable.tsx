// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Tooltip, useDisclosure } from '@heroui/react';
import {
  IconAlertTriangle,
  IconExternalLink,
  IconEye,
  IconTrash,
} from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo, useState } from 'react';

import { useTranslation } from 'next-i18next';
import router from 'next/router';

import { useAccessControl } from '@/hooks/useAccessControl';
import { useSystemToast } from '@amdenterpriseai/hooks';

import {
  deleteProject as deleteProjectAPI,
  fetchSubmittableProjects,
} from '@/services/app';

import { APIRequestError } from '@amdenterpriseai/utils/app';
import {
  formatGpuAllocation,
  formatCpuAllocation,
  formatMemoryAllocation,
} from '@amdenterpriseai/utils/app';
import { isHttpUrl, stripTrailingSlashes } from '@amdenterpriseai/utils/app';

import { TableColumns } from '@amdenterpriseai/types';
import { ProjectsResponse } from '@/types/projects';
import { CustomComparatorConfig } from '@amdenterpriseai/types';
import { ProjectTableField } from '@/types/enums/project-table-fields';
import { ProjectWithResourceAllocation } from '@/types/projects';

import { ConfirmationModal } from '@amdenterpriseai/components';
import { ClientSideDataTable } from '@amdenterpriseai/components';
import { StatusDisplay } from '@amdenterpriseai/components';

import { ProjectStatus } from '@/types/enums/projects';
import { getProjectStatusVariants } from '@/utils/projects-status-variants';

import { StatusError } from '@amdenterpriseai/components';

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

  const { isAdministrator } = useAccessControl();
  const { data: userProjects } = useQuery<ProjectsResponse>({
    queryKey: ['user-projects'],
    queryFn: fetchSubmittableProjects,
    enabled: !isAdministrator,
  });

  const isRowDisabled = useCallback(
    (project: ProjectWithResourceAllocation) => {
      if (isAdministrator) return false;
      return !userProjects?.data.some((p) => p.id === project.id);
    },
    [userProjects?.data, isAdministrator],
  );

  const [targetProject, setTargetProject] =
    useState<ProjectWithResourceAllocation | null>(null);

  const {
    isOpen: isDeleteModalOpen,
    onOpen: onDeleteModalOpen,
    onOpenChange: onDeleteModalOpenChange,
  } = useDisclosure();

  const openProjectDetails = useCallback((id: string) => {
    router.push(`/projects/${id}`);
  }, []);

  const actions = useMemo(
    () => [
      {
        key: 'openDetails',
        onPress: (p: ProjectWithResourceAllocation) => openProjectDetails(p.id),
        label: t('list.projects.actions.openDetails.label'),
        startContent: <IconEye />,
      },
      {
        key: 'viewInAiwb',
        onPress: (p: ProjectWithResourceAllocation) => {
          window.open(
            `${stripTrailingSlashes(p.cluster!.workbenchBaseUrl!)}/${p.name}`,
            '_blank',
            'noopener,noreferrer',
          );
        },
        label: t('list.projects.actions.viewInAiwb.label'),
        startContent: <IconExternalLink />,
        isDisabled: (p: ProjectWithResourceAllocation) =>
          !p.cluster?.workbenchBaseUrl ||
          !isHttpUrl(p.cluster.workbenchBaseUrl),
        showDivider: true,
      },
      {
        key: 'delete',
        className: 'text-danger',
        color: 'danger',
        onPress: (p: ProjectWithResourceAllocation) => {
          setTargetProject(p);
          onDeleteModalOpen();
        },
        isDisabled: !isAdministrator,
        label: t('list.projects.actions.delete.label'),
        startContent: <IconTrash />,
      },
    ],
    [isAdministrator, onDeleteModalOpen, openProjectDetails, t],
  );

  const customRenderers: Partial<
    Record<
      ProjectTableField,
      (item: ProjectWithResourceAllocation) => React.ReactNode | string
    >
  > = {
    [ProjectTableField.STATUS]: (item) => (
      <StatusDisplay
        type={item.status}
        variants={getProjectStatusVariants(t)}
        additionalProps={
          item.status === ProjectStatus.FAILED && !!item.statusReason
            ? {
                isClickable: true,
                helpContent: <StatusError statusReason={item.statusReason} />,
              }
            : undefined
        }
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
              <IconAlertTriangle size={16} className="text-warning" />
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
              <IconAlertTriangle size={16} className="text-warning" />
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
              <IconAlertTriangle size={16} className="text-warning" />
            </Tooltip>
          </div>
        );
      }

      return allocation;
    },
  };

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
        isRowDisabled={isRowDisabled}
        className="overflow-y-auto"
      />
      <ConfirmationModal
        confirmationButtonColor="danger"
        description={t('settings.delete.confirmation.description', {
          project: targetProject?.name,
        })}
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
