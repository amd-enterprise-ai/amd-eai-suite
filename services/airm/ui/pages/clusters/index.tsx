// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Accordion, AccordionItem, useDisclosure } from '@heroui/react';
import {
  IconCircleCaretRightFilled,
  IconCircleCheck,
  IconCircleCheckFilled,
  IconCircleXFilled,
  IconLoader2,
} from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo, useState } from 'react';

import { getServerSession } from 'next-auth';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';
import router from 'next/router';

import useSystemToast from '@/hooks/useSystemToast';

import {
  deleteCluster as deleteClusterAPI,
  fetchClusters,
} from '@/services/app/clusters';
import { getWorkloadsStats as fetchWorkloadsStats } from '@/services/app/workloads';
import { getClusters } from '@/services/server/clusters';
import { getWorkloadsStats } from '@/services/server/workloads';

import { getFilteredData } from '@/utils/app/data-table';
import { APIRequestError } from '@/utils/app/errors';
import {
  formatGpuAllocation,
  formatCpuAllocation,
  formatMemoryAllocation,
} from '@/utils/app/strings';
import { authOptions } from '@/utils/server/auth';

import { Cluster, ClustersResponse } from '@/types/clusters';
import { TableColumns } from '@/types/data-table/clientside-table';
import { CustomComparatorConfig } from '@/types/data-table/table-comparators';
import { ClusterStatus } from '@/types/enums/cluster-status';
import {
  ClusterTableField,
  PendingClusterTableField,
} from '@/types/enums/cluster-table-fields';
import { FilterComponentType } from '@/types/enums/filters';
import { ClientSideDataFilter, FilterValueMap } from '@/types/filters';
import { WorkloadsStats } from '@/types/workloads';

import { ClustersStats, EditCluster } from '@/components/features/clusters';
import ConnectClusterModal from '@/components/features/clusters/ConnectClusterModal';
import { ConfirmationModal } from '@/components/shared/Confirmation/ConfirmationModal';
import ClientSideDataTable from '@/components/shared/DataTable/ClientSideDataTable';
import { ActionsToolbar } from '@/components/shared/Toolbar/ActionsToolbar';
import { ActionButton } from '@/components/shared/Buttons';
import { format } from 'date-fns';
import { doesDataNeedToBeRefreshed } from '@/utils/app/clusters';
import { DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA } from '@/utils/app/api-helpers';

const activeClusterCustomComparators: CustomComparatorConfig<
  Cluster,
  ClusterTableField
> = {
  [ClusterTableField.NODES]: (a: Cluster, b: Cluster): number =>
    a.availableNodeCount - b.availableNodeCount,
  [ClusterTableField.GPU_ALLOCATION]: (a: Cluster, b: Cluster): number =>
    a.allocatedResources.gpuCount - b.allocatedResources.gpuCount,
  [ClusterTableField.CPU_ALLOCATION]: (a: Cluster, b: Cluster): number =>
    a.allocatedResources.cpuMilliCores - b.allocatedResources.cpuMilliCores,
  [ClusterTableField.MEMORY_ALLOCATION]: (a: Cluster, b: Cluster): number =>
    a.allocatedResources.memoryBytes - b.allocatedResources.memoryBytes,
};

const activeClusterColumns: TableColumns<ClusterTableField> = [
  { key: ClusterTableField.NAME, sortable: true },
  { key: ClusterTableField.STATUS, sortable: true },
  { key: ClusterTableField.NODES, sortable: true, hasDescription: true },
  { key: ClusterTableField.GPU_ALLOCATION, sortable: true },
  { key: ClusterTableField.CPU_ALLOCATION, sortable: true },
  { key: ClusterTableField.MEMORY_ALLOCATION, sortable: true },
];

const pendingClusterColumns: TableColumns<PendingClusterTableField> = [
  { key: PendingClusterTableField.REQUESTED_AT, sortable: true },
  // TODO: show expiry date when expiry feature is available and implemented
  // { key: PendingClusterTableField.REQUESTED_EXPIRY, sortable: true },
  { key: PendingClusterTableField.STATUS },
];

interface Props {
  clusters: ClustersResponse;
  workloadsStats: WorkloadsStats;
}

const ClustersPage = ({ clusters, workloadsStats }: Props) => {
  const { t } = useTranslation('clusters');
  const { toast } = useSystemToast();
  const [filters, setFilters] = useState<ClientSideDataFilter<Cluster>[]>([]);

  const {
    isOpen: isAddClusterModalOpen,
    onOpen: onAddClusterModalOpen,
    onOpenChange: onAddClusterModalOpenChange,
  } = useDisclosure();

  const {
    isOpen: isEditClusterOpen,
    onOpen: onEditClusterOpen,
    onOpenChange: onEditClusterOpenChange,
  } = useDisclosure();

  const {
    isOpen: isDeleteClusterModalOpen,
    onOpen: onDeleteClusterModalOpen,
    onOpenChange: onDeleteClusterModalOpenChange,
  } = useDisclosure();

  const {
    data,
    isFetching: isFetchingClusters,
    dataUpdatedAt: clustersUpdatedAt,
    refetch: refetchClusters,
  } = useQuery<ClustersResponse>({
    queryKey: ['clusters'],
    queryFn: fetchClusters,
    initialData: clusters,
    refetchInterval: (query) => {
      return !query.state.data ||
        doesDataNeedToBeRefreshed(query.state.data.clusters)
        ? DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA
        : false;
    },
  });

  const { data: workloadsStatsData } = useQuery<WorkloadsStats>({
    queryKey: ['workloads', 'stats'],
    queryFn: () => fetchWorkloadsStats(),
    initialData: workloadsStats,
  });

  const queryClient = useQueryClient();
  const [clusterBeingDeleted, setClusterBeingDeleted] = useState<Cluster>();
  const [clusterBeingEdited, setClusterBeingEdited] = useState<Cluster>();

  const { mutate: deleteCluster, isPending: isDeleteClusterPending } =
    useMutation({
      mutationFn: deleteClusterAPI,
      onSuccess: () => {
        onDeleteClusterModalOpenChange();
        queryClient.invalidateQueries({ queryKey: ['clusters'] });
        toast.success(
          t(
            `list.actions.${clusterBeingDeleted?.name ? 'delete' : 'cancel'}.notification.success`,
          ),
        );
      },
      onError: (error) => {
        onDeleteClusterModalOpenChange();

        toast.error(
          t(
            `list.actions.${clusterBeingDeleted?.name ? 'delete' : 'cancel'}.notification.error`,
          ),
          error as APIRequestError,
        );
      },
    });
  const clustersData = data.clusters;
  const filteredClusterData = useMemo(() => {
    if (!data?.clusters) {
      return [];
    }

    const activeClusters = data.clusters.filter(
      (item) => item.status !== ClusterStatus.VERIFYING,
    );

    return getFilteredData(activeClusters, filters);
  }, [data?.clusters, filters]);

  const pendingClusterData = useMemo(() => {
    if (!data?.clusters) {
      return [];
    }

    return data.clusters.filter(
      (item) => item.status === ClusterStatus.VERIFYING,
    );
  }, [data?.clusters]);

  const ClusterStatusDisplay = ({ status }: { status: ClusterStatus }) => (
    <div className="flex items-center space-x-2">
      {status === ClusterStatus.UNHEALTHY && (
        <IconCircleXFilled size={20} className="text-danger" />
      )}
      {status === ClusterStatus.HEALTHY && (
        <IconCircleCheckFilled size={20} className="text-success" />
      )}
      {status === ClusterStatus.VERIFYING && (
        <IconCircleCaretRightFilled size={20} className="text-primary" />
      )}
      <span className="text-sm">{t(`status.${status}`)}</span>
    </div>
  );

  const activeClusterCustomRenderers: Partial<
    Record<ClusterTableField, (item: Cluster) => React.ReactNode | string>
  > = {
    [ClusterTableField.STATUS]: (item) => {
      return <ClusterStatusDisplay status={item.status} />;
    },
    [ClusterTableField.NODES]: (item) =>
      `${item.availableNodeCount} / ${item.totalNodeCount}`,
    [ClusterTableField.GPU_ALLOCATION]: (item) =>
      formatGpuAllocation(
        item.allocatedResources.gpuCount,
        item.gpuAllocationPercentage,
      ),
    [ClusterTableField.CPU_ALLOCATION]: (item) =>
      formatCpuAllocation(
        item.allocatedResources.cpuMilliCores,
        item.cpuAllocationPercentage,
      ),
    [ClusterTableField.MEMORY_ALLOCATION]: (item) =>
      formatMemoryAllocation(
        item.allocatedResources.memoryBytes,
        item.memoryAllocationPercentage,
      ),
  };

  const pendingClusterCustomRenderers: Partial<
    Record<
      PendingClusterTableField,
      (item: Cluster) => React.ReactNode | string
    >
  > = {
    [PendingClusterTableField.REQUESTED_AT]: (item) => {
      return item?.createdAt
        ? format(new Date(item.createdAt), 'yyyy-MM-dd hh:mm')
        : '-';
    },
    [PendingClusterTableField.STATUS]: () => {
      return (
        <div className="flex items-center space-x-2">
          <IconLoader2 size={20} className="text-warning animate-spin" />
          <span className="text-sm">{t('status.verifying')}</span>
        </div>
      );
    },
  };

  const actions = [
    {
      key: 'edit',
      className: 'text-danger',
      onPress: (c: Cluster) => {
        setClusterBeingEdited(c);
        onEditClusterOpen();
      },
      label: t('list.actions.edit.label'),
    },
    {
      key: 'delete',
      className: 'text-danger',
      color: 'danger',
      onPress: (c: Cluster) => {
        setClusterBeingDeleted(c);
        onDeleteClusterModalOpen();
      },
      label: t('list.actions.delete.label'),
    },
  ];

  const pendingClustersActions = [
    {
      key: 'delete',
      className: 'text-danger',
      color: 'danger',
      onPress: (c: Cluster) => {
        setClusterBeingDeleted(c);
        onDeleteClusterModalOpen();
      },
      label: t('list.actions.delete.label'),
    },
  ];

  const handleFilterChange = useCallback(
    (filters: FilterValueMap) => {
      const newFilters: ClientSideDataFilter<Cluster>[] = [];

      if (filters.search) {
        newFilters.push({
          values: filters.search,
          field: 'name',
        });
      }

      if (
        filters.status &&
        filters.status.length > 0 &&
        filters.status[0] !== ''
      ) {
        newFilters.push({
          values: filters.status,
          field: 'status',
          exact: true,
        });
      }

      setFilters(newFilters);
    },
    [setFilters],
  );

  const handleRowPressed = (id: string) => {
    router.push(`/clusters/${id}`);
  };

  const filterConfig = useMemo(
    () => ({
      search: {
        name: 'search',
        className: 'min-w-72',
        label: t('list.filter.search.label'),
        placeholder: t('list.filter.search.placeholder'),
        type: FilterComponentType.TEXT,
      },
      status: {
        name: 'status',
        label: t('list.filter.status.label'),
        allowEmptySelection: true,
        icon: <IconCircleCheck size={14} />,
        className: 'min-w-48',
        placeholder: t('list.filter.status.placeholder'),
        type: FilterComponentType.SELECT,
        fields: Object.values(ClusterStatus).map((status) => ({
          key: status,
          label: t(`status.${status}`),
        })),
      },
    }),
    [t],
  );

  return (
    <div className="inline-flex flex-col w-full h-full max-h-full">
      <ActionsToolbar
        filterConfig={filterConfig}
        onFilterChange={handleFilterChange}
        onRefresh={refetchClusters}
        updatedTimestamp={clustersUpdatedAt}
        isRefreshing={isFetchingClusters}
        endContent={
          <ActionButton
            aria-label={t('actions.connect') || ''}
            onPress={onAddClusterModalOpen}
          >
            {t('actions.connect')}
          </ActionButton>
        }
      />
      <ClustersStats
        clusters={clustersData}
        workloadsStats={workloadsStatsData}
      />
      <Accordion
        selectionMode="multiple"
        defaultExpandedKeys={[
          'accordion-active-clusters',
          'accordion-pending-clusters',
        ]}
      >
        <AccordionItem
          title={t('list.active.title')}
          key="accordion-active-clusters"
        >
          <ClientSideDataTable
            data={filteredClusterData}
            className="flex-1 overflow-y-auto"
            columns={activeClusterColumns}
            defaultSortByField={ClusterTableField.NAME}
            translation={t}
            customRenderers={activeClusterCustomRenderers}
            customComparator={activeClusterCustomComparators}
            idKey={'id'}
            rowActions={actions}
            onRowPressed={handleRowPressed}
          />
        </AccordionItem>
        {pendingClusterData.length > 0 ? (
          <AccordionItem
            title={t('list.pending.title')}
            key="accordion-pending-clusters"
          >
            <ClientSideDataTable
              data={pendingClusterData}
              className="flex-1 overflow-y-auto"
              columns={pendingClusterColumns}
              defaultSortByField={PendingClusterTableField.REQUESTED_AT}
              translation={t}
              translationKeyPrefix="pending"
              customRenderers={pendingClusterCustomRenderers}
              customComparator={activeClusterCustomComparators}
              idKey="id"
              rowActions={pendingClustersActions}
            />
          </AccordionItem>
        ) : null}
      </Accordion>

      <ConnectClusterModal
        isOpen={isAddClusterModalOpen}
        onOpenChange={onAddClusterModalOpenChange}
      />

      <EditCluster
        isOpen={!!clusterBeingEdited && isEditClusterOpen}
        onOpenChange={onEditClusterOpenChange}
        cluster={clusterBeingEdited!}
      />

      <ConfirmationModal
        confirmationButtonColor="danger"
        description={t(
          `list.actions.${clusterBeingDeleted?.name ? 'delete' : 'cancel'}.confirmation.description`,
        )}
        title={t(
          `list.actions.${clusterBeingDeleted?.name ? 'delete' : 'cancel'}.confirmation.title`,
        )}
        isOpen={isDeleteClusterModalOpen}
        loading={isDeleteClusterPending}
        onConfirm={() => deleteCluster(clusterBeingDeleted?.id!)}
        onClose={onDeleteClusterModalOpenChange}
      />
    </div>
  );
};

export default ClustersPage;

export async function getServerSideProps(context: any) {
  const { locale } = context;

  const session = await getServerSession(context.req, context.res, authOptions);

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

  const [clusters, workloadsStats] = await Promise.all([
    getClusters(session?.accessToken as string),
    getWorkloadsStats(session?.accessToken as string),
  ]);

  return {
    props: {
      ...(await serverSideTranslations(locale, ['common', 'clusters'])),
      clusters,
      workloadsStats,
    },
  };
}
