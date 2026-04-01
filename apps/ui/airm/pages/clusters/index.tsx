// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { Accordion, AccordionItem, useDisclosure } from '@heroui/react';
import { IconCircleCheck } from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo, useState } from 'react';

import { getServerSession } from 'next-auth';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';
import router from 'next/router';

import { useAccessControl } from '@/hooks/useAccessControl';
import { useSystemToast } from '@amdenterpriseai/hooks';

import {
  deleteCluster as deleteClusterAPI,
  fetchClusters,
} from '@/services/app';
import { getWorkloadsStats as fetchWorkloadsStats } from '@/services/app';
import { getClusters } from '@/services/server';
import { getWorkloadsStats } from '@/services/server';

import {
  airmMenuItems,
  doesClusterDataNeedToBeRefreshed,
  getAuthRedirect,
  getFilteredData,
  dateComparator,
} from '@amdenterpriseai/utils/app';
import { APIRequestError } from '@amdenterpriseai/utils/app';
import {
  formatGpuAllocation,
  formatCpuAllocation,
  formatMemoryAllocation,
} from '@amdenterpriseai/utils/app';
import { authOptions } from '@amdenterpriseai/utils/server';

import { Cluster, ClustersResponse } from '@amdenterpriseai/types';
import { TableColumns } from '@amdenterpriseai/types';
import { CustomComparatorConfig } from '@amdenterpriseai/types';
import { ClusterStatus } from '@amdenterpriseai/types';
import {
  ClusterTableField,
  PendingClusterTableField,
} from '@amdenterpriseai/types';
import { FilterComponentType } from '@amdenterpriseai/types';
import { ClientSideDataFilter, FilterValueMap } from '@amdenterpriseai/types';
import { WorkloadsStats } from '@amdenterpriseai/types';

import { ClustersStats, EditCluster } from '@/components/features/clusters';
import ConnectClusterModal from '@/components/features/clusters/ConnectClusterModal';
import { ConfirmationModal } from '@amdenterpriseai/components';
import { ClientSideDataTable } from '@amdenterpriseai/components';
import { ActionsToolbar } from '@amdenterpriseai/components';
import { ActionButton } from '@amdenterpriseai/components';
import { DEFAULT_REFETCH_INTERVAL_FOR_PENDING_DATA } from '@amdenterpriseai/utils/app';
import {
  StatusDisplay,
  NoDataDisplay,
  DateDisplay,
} from '@amdenterpriseai/components';
import { getClusterStatusVariants } from '@amdenterpriseai/utils/app';
import { Status } from '@amdenterpriseai/components';

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

const pendingClusterCustomComparators: CustomComparatorConfig<
  Cluster,
  PendingClusterTableField
> = {
  [PendingClusterTableField.REQUESTED_AT]: (a, b) =>
    dateComparator(a.createdAt, b.createdAt),
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
  { key: PendingClusterTableField.STATUS, sortable: true },
];

interface Props {
  clusters: ClustersResponse;
  workloadsStats: WorkloadsStats;
}

const ClustersPage = ({ clusters, workloadsStats }: Props) => {
  const { t } = useTranslation('clusters');
  const { toast } = useSystemToast();
  const { isAdministrator } = useAccessControl();
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
        doesClusterDataNeedToBeRefreshed(query.state.data.data)
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
            `list.actions.${
              clusterBeingDeleted?.name ? 'delete' : 'cancel'
            }.notification.success`,
          ),
        );
      },
      onError: (error) => {
        onDeleteClusterModalOpenChange();

        toast.error(
          t(
            `list.actions.${
              clusterBeingDeleted?.name ? 'delete' : 'cancel'
            }.notification.error`,
          ),
          error as APIRequestError,
        );
      },
    });
  const clustersData = data.data;
  const filteredClusterData = useMemo(() => {
    if (!data?.data) {
      return [];
    }

    const activeClusters = data.data.filter(
      (item) => item.status !== ClusterStatus.VERIFYING,
    );

    return getFilteredData(activeClusters, filters);
  }, [data?.data, filters]);

  const pendingClusterData = useMemo(() => {
    if (!data?.data) {
      return [];
    }

    return data.data.filter((item) => item.status === ClusterStatus.VERIFYING);
  }, [data?.data]);

  const activeClusterCustomRenderers: Partial<
    Record<ClusterTableField, (item: Cluster) => React.ReactNode | string>
  > = {
    [ClusterTableField.STATUS]: (item) => (
      <StatusDisplay
        type={item.status}
        variants={getClusterStatusVariants(t)}
      />
    ),
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
      return item?.createdAt ? (
        <DateDisplay date={item.createdAt} />
      ) : (
        <NoDataDisplay />
      );
    },
    [PendingClusterTableField.STATUS]: () => {
      return (
        <Status {...getClusterStatusVariants(t)[ClusterStatus.VERIFYING]} />
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
          isAdministrator ? (
            <ActionButton
              aria-label={t('actions.connect') || ''}
              onPress={onAddClusterModalOpen}
            >
              {t('actions.connect')}
            </ActionButton>
          ) : undefined
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
            rowActions={isAdministrator ? actions : undefined}
            onRowPressed={handleRowPressed}
          />
        </AccordionItem>
        {isAdministrator && pendingClusterData.length > 0 ? (
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
              customComparator={pendingClusterCustomComparators}
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

      {clusterBeingEdited && (
        <EditCluster
          isOpen={isEditClusterOpen}
          onOpenChange={onEditClusterOpenChange}
          cluster={clusterBeingEdited}
        />
      )}

      <ConfirmationModal
        confirmationButtonColor="danger"
        description={t(
          `list.actions.${
            clusterBeingDeleted?.name ? 'delete' : 'cancel'
          }.confirmation.description`,
        )}
        title={t(
          `list.actions.${
            clusterBeingDeleted?.name ? 'delete' : 'cancel'
          }.confirmation.title`,
        )}
        isOpen={isDeleteClusterModalOpen}
        loading={isDeleteClusterPending}
        onConfirm={() =>
          clusterBeingDeleted && deleteCluster(clusterBeingDeleted.id)
        }
        onClose={onDeleteClusterModalOpenChange}
      />
    </div>
  );
};

export default ClustersPage;

export async function getServerSideProps(context: any) {
  const { locale } = context;

  const session = await getServerSession(context.req, context.res, authOptions);

  // Redirect unauthenticated users to '/'
  const authRedirect = getAuthRedirect(session, airmMenuItems);
  if (authRedirect && !session?.user) {
    return authRedirect;
  }

  const [clusters, workloadsStats = []] = await Promise.all([
    getClusters(session?.accessToken as string),
    getWorkloadsStats(session?.accessToken as string),
  ]);

  return {
    props: {
      ...(await serverSideTranslations(locale, [
        'common',
        'sharedComponents',
        'clusters',
      ])),
      clusters,
      workloadsStats,
    },
  };
}
