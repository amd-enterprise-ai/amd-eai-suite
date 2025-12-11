// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useDisclosure } from '@heroui/react';
import {
  IconExternalLink,
  IconEye,
  IconFileText,
  IconMessage,
  IconTrash,
} from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';

import { getServerSession } from 'next-auth';
import { useRouter } from 'next/router';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import useSystemToast from '@/hooks/useSystemToast';

import { deleteWorkload, listWorkloads } from '@/services/app/workloads';

import { getFilteredData } from '@/utils/app/data-table';
import { displayMegabytesInGigabytes } from '@/utils/app/memory';
import getWorkloadStatusVariants from '@/utils/app/workloads-status-variants';
import getWorkloadTypeVariants from '@/utils/app/workloads-type-variants';
import { authOptions } from '@/utils/server/auth';

import { ActionItem, TableColumns } from '@/types/data-table/clientside-table';
import { FilterComponentType } from '@/types/enums/filters';
import { SortDirection } from '@/types/enums/sort-direction';
import { WorkloadStatus, WorkloadType } from '@/types/enums/workloads';
import { WorkloadsTableFields } from '@/types/enums/workloads-table-fields';
import { ClientSideDataFilter, FilterValueMap } from '@/types/filters';
import { Workload } from '@/types/workloads';

import DeleteWorkloadModal from '@/components/features/workloads/DeleteWorkloadModal';
import WorkloadLogsModal from '@/components/features/workloads/WorkloadLogsModal';
import ClientSideDataTable from '@/components/shared/DataTable/ClientSideDataTable';
import {
  ChipDisplay,
  DateDisplay,
  NoDataDisplay,
  StatusDisplay,
  TranslationDisplay,
} from '@/components/shared/DataTable/CustomRenderers';
import { ActionsToolbar } from '@/components/shared/Toolbar/ActionsToolbar';

import { useProject } from '@/contexts/ProjectContext';

const defaultStatusSet = Object.values(WorkloadStatus).filter(
  (status) => status !== WorkloadStatus.DELETED,
);

const defaultTypeSet = Object.values(WorkloadType);

const columns: TableColumns<WorkloadsTableFields | null> = [
  {
    key: WorkloadsTableFields.DISPLAY_NAME,
    sortable: true,
  },
  {
    key: WorkloadsTableFields.VRAM,
    sortable: true,
  },
  {
    key: WorkloadsTableFields.GPU,
    sortable: true,
  },
  {
    key: WorkloadsTableFields.TYPE,
    sortable: true,
  },
  {
    key: WorkloadsTableFields.CREATED_BY,
    sortable: true,
  },
  {
    key: WorkloadsTableFields.CREATED_AT,
    sortable: true,
  },
  {
    key: WorkloadsTableFields.STATUS,
    sortable: true,
  },
];

const convertFilterValueMap = (
  filters: FilterValueMap,
): ClientSideDataFilter<Workload>[] => {
  const newFilters: ClientSideDataFilter<Workload>[] = [];
  if (filters?.search) {
    newFilters.push({
      field: 'displayName',
      values: filters.search,
    });
  }
  if (filters?.status) {
    newFilters.push({
      field: 'status',
      values: filters.status,
    });
  }
  if (filters?.type) {
    newFilters.push({
      field: 'type',
      values: filters.type,
    });
  }
  return newFilters;
};

const WorkloadsPage: React.FC = () => {
  const { t } = useTranslation(['workloads', 'models']);
  const { toast } = useSystemToast();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { activeProject } = useProject();

  const [workloadBeingSelected, setWorkloadBeingSelected] = useState<
    Workload | undefined
  >(undefined);

  const typeFilterItems = useMemo(
    () => [
      {
        key: WorkloadType.MODEL_DOWNLOAD,
        label: t(`type.${WorkloadType.MODEL_DOWNLOAD}`),
      },
      {
        key: WorkloadType.INFERENCE,
        label: t(`type.${WorkloadType.INFERENCE}`),
      },
      {
        key: WorkloadType.FINE_TUNING,
        label: t(`type.${WorkloadType.FINE_TUNING}`),
      },
      {
        key: WorkloadType.WORKSPACE,
        label: t(`type.${WorkloadType.WORKSPACE}`),
      },
      {
        key: WorkloadType.CUSTOM,
        label: t(`type.${WorkloadType.CUSTOM}`),
      },
    ],
    [t],
  );

  const statusFilterItems = useMemo(
    () => [
      {
        key: WorkloadStatus.ADDED,
        label: t(`status.${WorkloadStatus.ADDED}`),
      },
      {
        key: WorkloadStatus.PENDING,
        label: t(`status.${WorkloadStatus.PENDING}`),
      },
      {
        key: WorkloadStatus.RUNNING,
        label: t(`status.${WorkloadStatus.RUNNING}`),
      },
      {
        key: WorkloadStatus.TERMINATED,
        label: t(`status.${WorkloadStatus.TERMINATED}`),
      },
      {
        key: WorkloadStatus.COMPLETE,
        label: t(`status.${WorkloadStatus.COMPLETE}`),
      },
      {
        key: WorkloadStatus.FAILED,
        label: t(`status.${WorkloadStatus.FAILED}`),
      },
      {
        key: WorkloadStatus.UNKNOWN,
        label: t(`status.${WorkloadStatus.UNKNOWN}`),
      },
      {
        key: WorkloadStatus.DELETING,
        label: t(`status.${WorkloadStatus.DELETING}`),
      },
      {
        key: WorkloadStatus.DELETE_FAILED,
        label: t(`status.${WorkloadStatus.DELETE_FAILED}`),
        showDivider: true,
      },
      {
        key: WorkloadStatus.DELETED,
        label: t(`status.${WorkloadStatus.DELETED}`),
      },
    ],
    [t],
  );

  const filterConfig = useMemo(
    () => ({
      search: {
        name: 'search',
        className: 'min-w-72',
        label: t('list.filters.search.placeholder'),
        placeholder: t('list.filters.search.placeholder'),
        type: FilterComponentType.TEXT,
      },
      type: {
        name: 'type',
        label: t('list.filters.type.label'),
        className: 'min-w-32',
        placeholder: t('list.filters.status.label'),
        type: FilterComponentType.DROPDOWN,
        defaultSelectedValues: defaultTypeSet.map(String),
        fields: typeFilterItems,
      },
      status: {
        name: 'status',
        className: 'min-w-32',
        label: t('list.filters.status.label'),
        placeholder: t('list.filters.status.label'),
        type: FilterComponentType.DROPDOWN,
        defaultSelectedValues: defaultStatusSet.map(String),
        fields: statusFilterItems,
      },
    }),
    [t, typeFilterItems, statusFilterItems],
  );

  const [filters, setFilters] = useState<ClientSideDataFilter<Workload>[]>(
    convertFilterValueMap({
      type: defaultTypeSet,
      status: defaultStatusSet,
    }),
  );

  const {
    data: allWorkloads,
    isLoading: isWorkloadsLoading,
    isRefetching: isWorkloadsRefetching,
    refetch: refetchWorkloads,
    error: workloadsError,
    dataUpdatedAt,
  } = useQuery<Workload[]>({
    queryKey: ['project', activeProject, 'workloads'],
    queryFn: async () => {
      return await listWorkloads(activeProject!, { withResources: true });
    },
    refetchInterval: 30000,
  });

  useEffect(() => {
    if (workloadsError) {
      toast.error(
        t('notifications.refresh.error', {
          error: String(workloadsError.message),
        }),
      );
    }
  }, [workloadsError, toast, t]);

  const workloads = useMemo(() => {
    if (!allWorkloads) return [];

    return getFilteredData(allWorkloads, filters);
  }, [allWorkloads, filters]);

  const { mutate: deleteWorkloadMutated } = useMutation({
    mutationFn: deleteWorkload,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['project', activeProject, 'workloads'],
      });
      toast.success(t('list.actions.delete.notification.success'));
    },
    onError: (_) => {
      toast.error(t('list.actions.delete.notification.error'));
    },
  });

  const {
    isOpen: isDeleteWorkloadModalOpen,
    onOpen: onDeleteWorkloadModalOpen,
    onOpenChange: onDeleteWorkloadModalOpenChange,
  } = useDisclosure();

  const {
    isOpen: isWorkloadLogsModalOpen,
    onOpen: onWorkloadLogsModalOpen,
    onOpenChange: onWorkloadLogsModalOpenChange,
  } = useDisclosure();

  const customRenderers: Partial<
    Record<WorkloadsTableFields, (item: Workload) => React.ReactNode | string>
  > = {
    [WorkloadsTableFields.VRAM]: (item) => {
      return !item.allocatedResources?.vram ? (
        <NoDataDisplay />
      ) : (
        <TranslationDisplay
          ns="workloads"
          tKey="list.valueTemplates.vram"
          value={displayMegabytesInGigabytes(item.allocatedResources?.vram)}
        />
      );
    },
    [WorkloadsTableFields.GPU]: (item) => {
      return !item.allocatedResources?.gpuCount ? (
        <NoDataDisplay />
      ) : (
        <TranslationDisplay
          ns="workloads"
          tKey="list.valueTemplates.gpu"
          value={item.allocatedResources?.gpuCount}
        />
      );
    },
    [WorkloadsTableFields.CREATED_AT]: (item) => (
      <DateDisplay date={item.createdAt} />
    ),
    [WorkloadsTableFields.TYPE]: (item: Workload) => (
      <ChipDisplay
        type={item[WorkloadsTableFields.TYPE] as WorkloadType}
        variants={getWorkloadTypeVariants(t)}
      />
    ),
    [WorkloadsTableFields.STATUS]: (item: Workload) => (
      <StatusDisplay
        type={item[WorkloadsTableFields.STATUS] as WorkloadStatus}
        variants={getWorkloadStatusVariants(t)}
      />
    ),
  };

  const actions = useMemo(
    () => (item: Workload) => {
      const actionsList: ActionItem<Workload>[] = [];

      actionsList.push({
        key: 'details',
        label: t('list.actions.details.label'),
        startContent: <IconEye />,
        onPress: (w: Workload) => {
          router.push(`/workloads/${w.id}`);
        },
      });

      if (
        item.type === WorkloadType.WORKSPACE &&
        (item.output?.externalHost || item.output?.host) &&
        item.status !== WorkloadStatus.DELETED
      ) {
        actionsList.push({
          isDisabled: item.status !== WorkloadStatus.RUNNING, // Enabled only in running state.
          key: 'openWorkspace',
          label: t('list.actions.openWorkspace.label'),
          startContent: <IconExternalLink />,
          onPress: () => {
            window.open(
              item.output?.externalHost || item.output?.host,
              '_blank',
            );
          },
        });
      }

      if (
        item.type === WorkloadType.INFERENCE &&
        item.status === WorkloadStatus.RUNNING
      ) {
        actionsList.push({
          key: 'chat',
          label: t('list.actions.chat.label'),
          startContent: <IconMessage />,
          onPress: () => {
            window.open(`/chat?workload=${item.id}`, '_blank');
          },
        });
      }

      actionsList.push({
        key: 'logs',
        label: t('list.actions.logs.label'),
        startContent: <IconFileText />,
        onPress: (w: Workload) => {
          setWorkloadBeingSelected(w);
          onWorkloadLogsModalOpen();
        },
      });

      if (item.status !== WorkloadStatus.DELETED) {
        actionsList.push({
          key: 'delete',
          label: t('list.actions.delete.label'),
          color: 'danger',
          startContent: <IconTrash />,
          onPress: (w: Workload) => {
            setWorkloadBeingSelected(w);
            onDeleteWorkloadModalOpen();
          },
        });
      }

      return actionsList;
    },
    [t, router, onWorkloadLogsModalOpen, onDeleteWorkloadModalOpen],
  );

  const handleFilterChange = (filters: FilterValueMap) => {
    const newFilters: ClientSideDataFilter<Workload>[] =
      convertFilterValueMap(filters);
    setFilters(newFilters);
  };

  const handleRefresh = () => {
    refetchWorkloads();
  };

  return (
    <div className="flex flex-col w-full">
      <ActionsToolbar
        filterConfig={filterConfig}
        onFilterChange={handleFilterChange}
        onRefresh={handleRefresh}
        isRefreshing={isWorkloadsLoading || isWorkloadsRefetching}
        updatedTimestamp={dataUpdatedAt}
      />
      <ClientSideDataTable
        data={workloads}
        className="flex-1 overflow-y-auto"
        columns={columns}
        rowActions={actions}
        defaultSortByField={WorkloadsTableFields.CREATED_AT}
        defaultSortDirection={SortDirection.DESC}
        translation={t}
        customRenderers={customRenderers}
        isLoading={isWorkloadsLoading}
        isFetching={isWorkloadsRefetching}
        idKey={'id'}
      />
      <DeleteWorkloadModal
        isOpen={isDeleteWorkloadModalOpen}
        onOpenChange={onDeleteWorkloadModalOpenChange}
        workload={workloadBeingSelected}
        onConfirmAction={deleteWorkloadMutated}
      />
      {isWorkloadLogsModalOpen && workloadBeingSelected && (
        <WorkloadLogsModal
          onOpenChange={onWorkloadLogsModalOpenChange}
          isOpen={isWorkloadLogsModalOpen}
          workload={workloadBeingSelected}
        />
      )}
    </div>
  );
};

export async function getServerSideProps(context: {
  req: any;
  res: any;
  locale: any;
}) {
  const { req, res, locale } = context;

  const session = await getServerSession(req, res, authOptions);

  if (
    !session ||
    !session.user ||
    !session.user.email ||
    !session.accessToken
  ) {
    return {
      redirect: {
        destination: '/',
        permanent: false,
      },
    };
  }

  return {
    props: {
      ...(await serverSideTranslations(locale, [
        'common',
        'models',
        'workloads',
      ])),
    },
  };
}

export default WorkloadsPage;
