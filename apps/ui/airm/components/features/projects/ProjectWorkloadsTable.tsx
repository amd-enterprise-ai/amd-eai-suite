// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useDisclosure } from '@heroui/react';
import { IconTrash } from '@tabler/icons-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useQuery } from '@tanstack/react-query';
import { Dispatch, SetStateAction, useMemo, useState } from 'react';

import { TFunction, useTranslation } from 'next-i18next';
import router from 'next/router';

import { useDebouncedCallback } from '@amdenterpriseai/hooks';
import { useSystemToast } from '@amdenterpriseai/hooks';

import { fetchProjectWorkloadsMetrics } from '@/services/app';
import { deleteWorkload } from '@/services/app';

import { convertToServerSideFilterParams } from '@amdenterpriseai/utils/app';
import { APIRequestError } from '@amdenterpriseai/utils/app';
import { displayMegabytesInGigabytes } from '@amdenterpriseai/utils/app';
import {
  displayTimestamp,
  formatDurationFromSeconds,
} from '@amdenterpriseai/utils/app';
import {
  getWorkloadStatusFilterItems,
  getWorkloadTypeFilterItems,
} from '@amdenterpriseai/utils/app';
import { getWorkloadStatusVariants } from '@amdenterpriseai/utils/app';
import { getWorkloadTypeVariants } from '@amdenterpriseai/utils/app';

import {
  CollectionRequestParams,
  CustomSortFieldMapperConfig,
  FilterParams,
} from '@amdenterpriseai/types';
import { TableColumns } from '@amdenterpriseai/types';
import { FilterComponentType } from '@amdenterpriseai/types';
import { ProjectWorkloadsTableField } from '@amdenterpriseai/types';
import { FilterOperator } from '@amdenterpriseai/types';
import { SortDirection } from '@amdenterpriseai/types';
import { WorkloadStatus, WorkloadType } from '@amdenterpriseai/types';
import { FilterValueMap } from '@amdenterpriseai/types';
import {
  WorkloadWithMetrics,
  WorkloadWithMetricsServer,
  ProjectWorkloadsMetricsResponse,
} from '@/types/workloads';

import DeleteWorkloadModal from '@/components/features/workloads/DeleteWorkloadModal';
import { ChipDisplay, StatusDisplay } from '@amdenterpriseai/components';
import { ServerSideDataTable } from '@amdenterpriseai/components';
import { ActionsToolbar } from '@amdenterpriseai/components';
import { ActionItem } from '@amdenterpriseai/types';

interface Props {
  projectId: string;
  rowActions?: (
    item: WorkloadWithMetrics,
    ...props: any[]
  ) => ActionItem<WorkloadWithMetrics>[];
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

const defaultFilterValues: FilterParams<WorkloadWithMetricsServer>[] = [
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

const defaultRowActions = (
  item: WorkloadWithMetrics,
  t: TFunction,
  setWorkloadSelected: Dispatch<
    SetStateAction<WorkloadWithMetrics | undefined>
  >,
  onDeleteWorkloadModalOpen: () => void,
) => {
  const canBeDeleted = ![
    WorkloadStatus.DELETED,
    WorkloadStatus.DELETING,
  ].includes(item.status);

  const actions = [];

  if (canBeDeleted) {
    actions.push({
      key: 'delete',
      label: t('list.workloads.actions.delete.title'),
      color: 'danger' as const,
      startContent: <IconTrash />,
      onPress: (w: WorkloadWithMetrics) => {
        setWorkloadSelected(w);
        onDeleteWorkloadModalOpen();
      },
    });
  }

  return actions;
};

const WORKLOADS_METRICS_QUERY_KEY = 'project';
const API_REQUEST_DEFAULTS: CollectionRequestParams<WorkloadWithMetricsServer> =
  {
    page: 1,
    pageSize: 10,
    sort: [
      {
        field: 'created_at' as keyof WorkloadWithMetricsServer,
        direction: SortDirection.DESC,
      },
    ],
    filter: defaultFilterValues,
  };

export const ProjectWorkloadsTable: React.FC<Props> = ({
  projectId,
  rowActions = defaultRowActions,
}) => {
  const { t } = useTranslation('projects');
  const { t: workloadsT } = useTranslation('workloads');
  const queryClient = useQueryClient();
  const { toast } = useSystemToast();

  const [workloadSelected, setWorkloadSelected] = useState<
    WorkloadWithMetrics | undefined
  >();

  const [filters, setFilters] =
    useState<Array<FilterParams<WorkloadWithMetricsServer>>>(
      defaultFilterValues,
    );

  const {
    isOpen: isDeleteWorkloadModalOpen,
    onOpen: onDeleteWorkloadModalOpen,
    onOpenChange,
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
    useState<CollectionRequestParams<WorkloadWithMetricsServer>>(
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
    enabled: !!projectId,
  });

  const handleWorkloadsTableParamsChange = useDebouncedCallback(
    (params: CollectionRequestParams<WorkloadWithMetricsServer>) => {
      setWorkloadsTableParams(params);
    },
    100,
  );

  const customRenderers: Partial<
    Record<
      ProjectWorkloadsTableField,
      (item: WorkloadWithMetrics) => React.ReactNode | string
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
    [ProjectWorkloadsTableField.RUN_TIME]: (item) =>
      item.runTime !== undefined
        ? `${formatDurationFromSeconds(item.runTime)}`
        : '-',
    [ProjectWorkloadsTableField.STATUS]: (item) => (
      <StatusDisplay
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
    WorkloadWithMetricsServer,
    ProjectWorkloadsTableField
  > = {
    [ProjectWorkloadsTableField.CREATED_AT]: { fields: ['created_at'] },
    [ProjectWorkloadsTableField.NAME]: { fields: ['display_name'] },
    [ProjectWorkloadsTableField.RUN_TIME]: {
      fields: ['run_time'],
    },
    [ProjectWorkloadsTableField.CREATED_BY]: { fields: ['created_by'] },
    [ProjectWorkloadsTableField.TYPE]: { fields: ['type'] },
    [ProjectWorkloadsTableField.STATUS]: { fields: ['status'] },
  };

  const typeFilterItems = useMemo(
    () => getWorkloadTypeFilterItems(workloadsT),
    [workloadsT],
  );

  const statusFilterItems = useMemo(
    () => getWorkloadStatusFilterItems(workloadsT),
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
    Record<string, (keyof WorkloadWithMetricsServer)[]>
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
            convertToServerSideFilterParams<WorkloadWithMetricsServer>(
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
        data={projectWorkloadsMetrics?.data ?? []}
        columns={columns}
        customRenderers={customRenderers}
        customSortFieldMapper={sortFieldMapper}
        defaultSortByField={ProjectWorkloadsTableField.CREATED_AT}
        defaultSortDirection={SortDirection.DESC}
        rowActions={(item) =>
          rowActions(item, t, setWorkloadSelected, onDeleteWorkloadModalOpen)
        }
        onRowPressed={(id: string) => {
          router.push(`/workloads/${id}`);
        }}
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
