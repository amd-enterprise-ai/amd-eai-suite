// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useDisclosure } from '@heroui/react';
import { IconTrash } from '@tabler/icons-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';

import { useTranslation } from 'next-i18next';

import { useDebouncedCallback } from '@/hooks/useDebouncedCallback';
import useSystemToast from '@/hooks/useSystemToast';

import { fetchProjectWorkloadsMetrics } from '@/services/app/projects';
import { deleteWorkload } from '@/services/app/workloads';

import { convertToServerSideFilterParams } from '@/utils/app/data-table';
import { APIRequestError } from '@/utils/app/errors';
import { displayMegabytesInGigabytes } from '@/utils/app/memory';
import {
  displayTimestamp,
  formatDurationFromSeconds,
} from '@/utils/app/strings';
import getWorkloadStatusVariants from '@/utils/app/workloads-status-variants';
import getWorkloadTypeVariants from '@/utils/app/workloads-type-variants';

import {
  CollectionRequestParams,
  CustomSortFieldMapperConfig,
  FilterParams,
} from '@/types/data-table/server-collection';
import { TableColumns } from '@/types/data-table/table';
import { FilterComponentType } from '@/types/enums/filters';
import { ProjectWorkloadsTableField } from '@/types/enums/project-workloads-table-field';
import { FilterOperator } from '@/types/enums/server-collection';
import { SortDirection } from '@/types/enums/sort-direction';
import { WorkloadStatus, WorkloadType } from '@/types/enums/workloads';
import { FilterValueMap } from '@/types/filters';
import {
  ProjectWorkloadWithMetrics,
  ProjectWorkloadWithMetricsServer,
} from '@/types/workloads';
import { ProjectWorkloadsMetricsResponse } from '@/types/workloads';

import DeleteWorkloadModal from '@/components/features/workloads/DeleteWorkloadModal';
import {
  ChipDisplay,
  StatusBadgeDisplay,
} from '@/components/shared/DataTable/CustomRenderers';
import ServerSideDataTable from '@/components/shared/DataTable/ServerSideDataTable';
import ActionsToolbar from '@/components/shared/Toolbar/ActionsToolbar';

interface Props {
  projectId: string;
}

const columns: TableColumns<ProjectWorkloadsTableField | null> = [
  {
    key: ProjectWorkloadsTableField.NAME,
    sortable: true,
  },
  {
    key: ProjectWorkloadsTableField.TYPE,
    sortable: true,
  },
  { key: ProjectWorkloadsTableField.STATUS, sortable: true },
  { key: ProjectWorkloadsTableField.GPUS },
  { key: ProjectWorkloadsTableField.VRAM },
  { key: ProjectWorkloadsTableField.CREATED_AT, sortable: true },
  { key: ProjectWorkloadsTableField.RUN_TIME, sortable: true },
  { key: ProjectWorkloadsTableField.CREATED_BY, sortable: true },
];

const defaultTypeSet = Object.values(WorkloadType);
const defaultStatusSet = Object.values(WorkloadStatus).filter(
  (status) => status !== WorkloadStatus.DELETED,
);

const defaultFilterValues: FilterParams<ProjectWorkloadWithMetricsServer>[] = [
  {
    fields: ['type'],
    operator: FilterOperator.EQ,
    values: defaultTypeSet,
  },
  {
    fields: ['status'],
    operator: FilterOperator.EQ,
    values: defaultStatusSet,
  },
];

const WORKLOADS_METRICS_QUERY_KEY = 'project';
const API_REQUEST_DEFAULTS: CollectionRequestParams<ProjectWorkloadWithMetricsServer> =
  {
    page: 1,
    pageSize: 10,
    sort: [
      {
        field: 'created_at' as keyof ProjectWorkloadWithMetricsServer,
        direction: SortDirection.DESC,
      },
    ],
    filter: defaultFilterValues,
  };

export const ProjectWorkloadsTable: React.FC<Props> = ({ projectId }) => {
  const { t } = useTranslation('projects');
  const { t: workloadsT } = useTranslation('workloads');
  const queryClient = useQueryClient();
  const { toast } = useSystemToast();

  const [workloadSelected, setWorkloadSelected] = useState<
    ProjectWorkloadWithMetrics | undefined
  >();

  const [filters, setFilters] =
    useState<Array<FilterParams<ProjectWorkloadWithMetricsServer>>>(
      defaultFilterValues,
    );

  const {
    isOpen: isDeleteWorkloadModalOpen,
    onOpen: onDeleteWorkloadModalOpen,
    onOpenChange: onOpenChange,
  } = useDisclosure();

  const { mutate: deleteWorkloadMutation } = useMutation({
    mutationFn: deleteWorkload,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', 'workloads'] });
      queryClient.invalidateQueries({
        queryKey: ['project', 'metrics', 'statuses'],
      });
      toast.success(t('list.workloads.actions.delete.notification.success'));
    },
    onError: (error) => {
      toast.error(
        t('list.workloads.actions.delete.notification.error'),
        error as APIRequestError,
      );
    },
  });

  const [workloadsTableParams, setWorkloadsTableParams] =
    useState<CollectionRequestParams<ProjectWorkloadWithMetricsServer>>(
      API_REQUEST_DEFAULTS,
    );

  const {
    data: projectWorkloadsMetrics,
    isFetching: isProjectWorkloadsMetricsLoading,
    refetch: refetchProjectWorkloadsMetrics,
    dataUpdatedAt: projectWorkloadsMetricsUpdatedAt,
  } = useQuery<ProjectWorkloadsMetricsResponse>({
    queryKey: [
      WORKLOADS_METRICS_QUERY_KEY,
      projectId,
      'workloads-metrics',
      workloadsTableParams,
    ],
    queryFn: () =>
      fetchProjectWorkloadsMetrics(projectId, workloadsTableParams),
  });

  const handleWorkloadsTableParamsChange = useDebouncedCallback(
    (params: CollectionRequestParams<ProjectWorkloadWithMetricsServer>) => {
      setWorkloadsTableParams(params);
    },
    100,
  );

  const customRenderers: Partial<
    Record<
      ProjectWorkloadsTableField,
      (item: ProjectWorkloadWithMetrics) => React.ReactNode | string
    >
  > = {
    [ProjectWorkloadsTableField.VRAM]: (item) =>
      displayMegabytesInGigabytes(item.vram),
    [ProjectWorkloadsTableField.CREATED_AT]: (item) => {
      if (item.createdAt) {
        return displayTimestamp(new Date(item.createdAt));
      }
      return '-';
    },
    [ProjectWorkloadsTableField.NAME]: (item) => {
      return item.displayName ?? '-';
    },
    [ProjectWorkloadsTableField.RUN_TIME]: (item) =>
      `${formatDurationFromSeconds(item.runTime)}`,
    [ProjectWorkloadsTableField.STATUS]: (item) => (
      <StatusBadgeDisplay
        type={item.status}
        variants={getWorkloadStatusVariants(workloadsT)}
      />
    ),
    [ProjectWorkloadsTableField.TYPE]: (item) => (
      <ChipDisplay
        type={item.type ?? t(`common.error.misc.unknownEntity`)}
        variants={getWorkloadTypeVariants(workloadsT)}
      />
    ),
  };

  const sortFieldMapper: CustomSortFieldMapperConfig<
    ProjectWorkloadWithMetricsServer,
    ProjectWorkloadsTableField
  > = {
    [ProjectWorkloadsTableField.CREATED_AT]: { fields: ['created_at'] },
    [ProjectWorkloadsTableField.NAME]: { fields: ['display_name'] },
    [ProjectWorkloadsTableField.RUN_TIME]: {
      fields: ['total_elapsed_seconds'],
    },
    [ProjectWorkloadsTableField.CREATED_BY]: { fields: ['created_by'] },
    [ProjectWorkloadsTableField.TYPE]: { fields: ['type'] },
    [ProjectWorkloadsTableField.STATUS]: { fields: ['status'] },
  };

  const rowActions = (item: ProjectWorkloadWithMetrics) => {
    const canBeDeleted = ![
      WorkloadStatus.DELETED,
      WorkloadStatus.DELETING,
    ].includes(item.status);

    return canBeDeleted
      ? [
          {
            key: 'delete',
            label: t('list.workloads.actions.delete.title'),
            color: 'danger',
            startContent: <IconTrash />,
            onPress: (w: ProjectWorkloadWithMetrics) => {
              setWorkloadSelected(w);
              onDeleteWorkloadModalOpen();
            },
          },
        ]
      : [];
  };

  const typeFilterItems = useMemo(
    () => [
      {
        key: WorkloadType.MODEL_DOWNLOAD,
        label: workloadsT(`type.${WorkloadType.MODEL_DOWNLOAD}`),
      },
      {
        key: WorkloadType.INFERENCE,
        label: workloadsT(`type.${WorkloadType.INFERENCE}`),
      },
      {
        key: WorkloadType.FINE_TUNING,
        label: workloadsT(`type.${WorkloadType.FINE_TUNING}`),
      },
      {
        key: WorkloadType.WORKSPACE,
        label: workloadsT(`type.${WorkloadType.WORKSPACE}`),
      },
      {
        key: WorkloadType.CUSTOM,
        label: workloadsT(`type.${WorkloadType.CUSTOM}`),
      },
    ],
    [workloadsT],
  );

  const statusFilterItems = useMemo(
    () => [
      {
        key: WorkloadStatus.ADDED,
        label: workloadsT(`status.${WorkloadStatus.ADDED}`),
      },
      {
        key: WorkloadStatus.PENDING,
        label: workloadsT(`status.${WorkloadStatus.PENDING}`),
      },
      {
        key: WorkloadStatus.RUNNING,
        label: workloadsT(`status.${WorkloadStatus.RUNNING}`),
      },
      {
        key: WorkloadStatus.TERMINATED,
        label: workloadsT(`status.${WorkloadStatus.TERMINATED}`),
      },
      {
        key: WorkloadStatus.COMPLETE,
        label: workloadsT(`status.${WorkloadStatus.COMPLETE}`),
      },
      {
        key: WorkloadStatus.FAILED,
        label: workloadsT(`status.${WorkloadStatus.FAILED}`),
      },
      {
        key: WorkloadStatus.UNKNOWN,
        label: workloadsT(`status.${WorkloadStatus.UNKNOWN}`),
      },
      {
        key: WorkloadStatus.DELETING,
        label: workloadsT(`status.${WorkloadStatus.DELETING}`),
      },
      {
        key: WorkloadStatus.DELETE_FAILED,
        label: workloadsT(`status.${WorkloadStatus.DELETE_FAILED}`),
        showDivider: true,
      },
      {
        key: WorkloadStatus.DELETED,
        label: workloadsT(`status.${WorkloadStatus.DELETED}`),
      },
    ],
    [workloadsT],
  );

  const filterConfig = useMemo(
    () => ({
      search: {
        name: 'search',
        label: workloadsT('list.filters.search.placeholder'),
        placeholder: workloadsT('list.filters.search.placeholder'),
        type: FilterComponentType.TEXT,
      },
      type: {
        name: 'type',
        label: workloadsT('list.filters.type.label'),
        placeholder: workloadsT('list.filters.status.label'),
        type: FilterComponentType.DROPDOWN,
        defaultSelectedValues: defaultTypeSet.map(String),
        fields: typeFilterItems,
      },
      status: {
        name: 'status',
        label: workloadsT('list.filters.status.label'),
        placeholder: workloadsT('list.filters.status.label'),
        type: FilterComponentType.DROPDOWN,
        defaultSelectedValues: defaultStatusSet.map(String),
        fields: statusFilterItems,
      },
    }),
    [workloadsT, typeFilterItems, statusFilterItems],
  );

  const operatorMapping = {
    search: FilterOperator.CONTAINS,
    type: FilterOperator.EQ,
    status: FilterOperator.EQ,
  };

  const serverSideFilterMapping: Partial<
    Record<string, (keyof ProjectWorkloadWithMetricsServer)[]>
  > = {
    search: ['display_name'],
    type: ['type'],
    status: ['status'],
  };

  return (
    <div>
      <ActionsToolbar
        filterConfig={filterConfig}
        onRefresh={refetchProjectWorkloadsMetrics}
        updatedTimestamp={projectWorkloadsMetricsUpdatedAt}
        isRefreshing={isProjectWorkloadsMetricsLoading}
        onFilterChange={(filters) => {
          const serverSideFilters =
            convertToServerSideFilterParams<ProjectWorkloadWithMetricsServer>(
              filters as FilterValueMap,
              operatorMapping,
              serverSideFilterMapping,
            );
          setFilters(serverSideFilters);
        }}
      />
      <ServerSideDataTable
        filters={filters}
        handleDataRequest={handleWorkloadsTableParamsChange}
        total={projectWorkloadsMetrics?.total ?? 0}
        data={projectWorkloadsMetrics?.workloads ?? []}
        columns={columns}
        customRenderers={customRenderers}
        customSortFieldMapper={sortFieldMapper}
        defaultSortByField={ProjectWorkloadsTableField.CREATED_AT}
        defaultSortDirection={SortDirection.DESC}
        rowActions={rowActions}
        translation={t}
        idKey="id"
        translationKeyPrefix="workloads"
        isLoading={isProjectWorkloadsMetricsLoading}
      />
      <DeleteWorkloadModal
        isOpen={isDeleteWorkloadModalOpen}
        onOpenChange={onOpenChange}
        workload={workloadSelected}
        onConfirmAction={deleteWorkloadMutation}
      />
    </div>
  );
};

export default ProjectWorkloadsTable;
