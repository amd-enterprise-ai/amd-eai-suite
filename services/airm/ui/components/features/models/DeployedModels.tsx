// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useDisclosure } from '@heroui/react';
import {
  IconExternalLink,
  IconEye,
  IconMessage,
  IconRocketOff,
} from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';

import { useRouter } from 'next/router';
import { Trans, useTranslation } from 'next-i18next';

import useSystemToast from '@/hooks/useSystemToast';

import { deleteWorkload, listWorkloads } from '@/services/app/workloads';
import { getAims } from '@/services/app/aims';
import { getModels } from '@/services/app/models';

import { getFilteredData } from '@/utils/app/data-table';
import getWorkloadStatusVariants from '@/utils/app/workloads-status-variants';
import getWorkloadTypeVariants from '@/utils/app/workloads-type-variants';

import { TableColumns } from '@/types/data-table/clientside-table';
import { FilterComponentType } from '@/types/enums/filters';
import { SortDirection } from '@/types/enums/sort-direction';
import { WorkloadStatus, WorkloadType } from '@/types/enums/workloads';
import { WorkloadsTableFields } from '@/types/enums/workloads-table-fields';
import { ClientSideDataFilter, FilterValueMap } from '@/types/filters';
import { Workload } from '@/types/workloads';

import { ConfirmationModal } from '@/components/shared/Confirmation/ConfirmationModal';
import ClientSideDataTable from '@/components/shared/DataTable/ClientSideDataTable';
import {
  ChipDisplay,
  DateDisplay,
  NoDataDisplay,
  StatusBadgeDisplay,
} from '@/components/shared/DataTable/CustomRenderers';
import { ActionsToolbar } from '@/components/shared/Toolbar/ActionsToolbar';

import { useProject } from '@/contexts/ProjectContext';

const defaultStatusSet = [
  WorkloadStatus.PENDING,
  WorkloadStatus.ADDED,
  WorkloadStatus.RUNNING,
  WorkloadStatus.FAILED,
  WorkloadStatus.DELETE_FAILED,
];

const defaultTypeSet = [
  WorkloadType.MODEL_DOWNLOAD,
  WorkloadType.INFERENCE,
  WorkloadType.FINE_TUNING,
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

interface DeployedModelsProps {}

const DeployedModels: React.FC<DeployedModelsProps> = ({}) => {
  const { t } = useTranslation(['workloads', 'models', 'common']);
  const { toast } = useSystemToast();
  const router = useRouter();
  const { activeProject } = useProject();

  const [filters, setFilters] = useState<ClientSideDataFilter<Workload>[]>(
    convertFilterValueMap({
      type: defaultTypeSet,
      status: defaultStatusSet,
    }),
  );

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

  const queryClient = useQueryClient();

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
      return await listWorkloads(activeProject!);
    },
    refetchInterval: 30000, // Refetch every 30 seconds
    enabled: !!activeProject,
  });

  const { data: aims, isLoading: isAimsLoading } = useQuery({
    queryKey: ['project', activeProject, 'aim-catalog'],
    queryFn: () => getAims(activeProject!),
    enabled: !!activeProject,
  });

  const { data: models, isLoading: isModelsLoading } = useQuery({
    queryKey: ['project', activeProject, 'models'],
    queryFn: () => getModels(activeProject!),
    enabled: !!activeProject,
  });

  // Create a mapping of aimId to canonicalName
  const aimIdToCanonicalName = useMemo(() => {
    const mapping = new Map<string, string>();
    if (aims) {
      aims.forEach((aim) => {
        // Extract canonical name from labels
        const canonicalNameKey = Object.keys(aim.labels).find((key) =>
          key.endsWith('.canonicalName'),
        );
        if (canonicalNameKey) {
          mapping.set(aim.id, aim.labels[canonicalNameKey]);
        }
      });
    }
    return mapping;
  }, [aims]);

  // Create a mapping of modelId to canonicalName
  const modelIdToCanonicalName = useMemo(() => {
    const mapping = new Map<string, string>();
    if (models) {
      models.forEach((model) => {
        mapping.set(model.id, model.canonicalName);
      });
    }
    return mapping;
  }, [models]);

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

    const filteredWorkloads = getFilteredData(allWorkloads, filters);
    return filteredWorkloads;
  }, [allWorkloads, filters]);

  const { mutate: deleteWorkloadMutated, isPending: isDeletePending } =
    useMutation({
      mutationFn: deleteWorkload,
      onSuccess: () => {
        queryClient.invalidateQueries({
          queryKey: ['project', activeProject, 'workloads'],
        });
        toast.success(t('list.actions.delete.notification.success'));
        onDeleteWorkloadModalClose();
      },
      onError: (_) => {
        toast.error(t('list.actions.delete.notification.error'));
      },
    });

  const {
    isOpen: isDeleteWorkloadModalOpen,
    onOpen: onDeleteWorkloadModalOpen,
    onClose: onDeleteWorkloadModalClose,
  } = useDisclosure();

  const columns: TableColumns<WorkloadsTableFields | null> = [
    {
      key: WorkloadsTableFields.DISPLAY_NAME,
      sortable: true,
    },
    {
      key: WorkloadsTableFields.CANONICAL_NAME,
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

  const customRenderers: Partial<
    Record<WorkloadsTableFields, (item: Workload) => React.ReactNode | string>
  > = {
    [WorkloadsTableFields.DISPLAY_NAME]: (item) =>
      item.model?.name || item.displayName || item.name,
    [WorkloadsTableFields.CANONICAL_NAME]: (item) => {
      // Try model canonical name via modelId first, then AIM canonical name via aimId
      const canonicalName =
        (item.modelId ? modelIdToCanonicalName.get(item.modelId) : undefined) ||
        (item.aimId ? aimIdToCanonicalName.get(item.aimId) : undefined);
      return canonicalName || <NoDataDisplay />;
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
      <StatusBadgeDisplay
        type={item[WorkloadsTableFields.STATUS] as WorkloadStatus}
        variants={getWorkloadStatusVariants(t)}
      />
    ),
  };

  const actions = (item: Workload) => {
    const actionsList = [];

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
      item.output?.internalHost &&
      item.status !== WorkloadStatus.DELETED
    ) {
      actionsList.push({
        key: 'openWorkspace',
        label: t('list.actions.openWorkspace.label'),
        startContent: <IconExternalLink />,
        onPress: () => {
          window.open(item.output?.internalHost, '_blank');
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
    if (item.status !== WorkloadStatus.DELETED) {
      actionsList.push({
        key: 'undeploy',
        label: t('customModels.list.actions.undeploy.label', { ns: 'models' }),
        color: 'danger',
        startContent: <IconRocketOff />,
        onPress: (w: Workload) => {
          setWorkloadBeingSelected(w);
          onDeleteWorkloadModalOpen();
        },
      });
    }

    return actionsList;
  };

  const filterConfig = useMemo(
    () => ({
      search: {
        name: 'search',
        label: t('list.filters.search.placeholder'),
        placeholder: t('list.filters.search.placeholder'),
        type: FilterComponentType.TEXT,
      },
      type: {
        name: 'type',
        label: t('list.filters.type.label'),
        placeholder: t('list.filters.status.label'),
        type: FilterComponentType.DROPDOWN,
        defaultSelectedValues: defaultTypeSet.map(String),
        fields: typeFilterItems,
      },
      status: {
        name: 'status',
        label: t('list.filters.status.label'),
        placeholder: t('list.filters.status.label'),
        type: FilterComponentType.DROPDOWN,
        defaultSelectedValues: defaultStatusSet.map(String),
        fields: statusFilterItems.map((field) => {
          return {
            props: {
              description: String(field.label),
              showDivider: field.showDivider,
            },
            key: String(field.key),
            label: t(field.label),
          };
        }),
      },
    }),
    [t, typeFilterItems, statusFilterItems],
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
    <div className="flex flex-col w-full" data-testid="deployed-models">
      <ActionsToolbar
        filterConfig={filterConfig}
        onFilterChange={handleFilterChange}
        isRefreshing={isWorkloadsRefetching}
        onRefresh={handleRefresh}
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
        isLoading={isWorkloadsLoading || isAimsLoading || isModelsLoading}
        isFetching={isWorkloadsRefetching}
        idKey={'id'}
      />
      <ConfirmationModal
        isOpen={isDeleteWorkloadModalOpen}
        onConfirm={() => deleteWorkloadMutated(workloadBeingSelected?.id || '')}
        description={
          <Trans parent="span">
            {t('customModels.list.actions.undeploy.confirmation.description', {
              ns: 'models',
              name:
                workloadBeingSelected?.model?.name ||
                workloadBeingSelected?.displayName ||
                '',
            })}
          </Trans>
        }
        title={t('customModels.list.actions.undeploy.confirmation.title', {
          ns: 'models',
        })}
        loading={isDeletePending}
        onClose={onDeleteWorkloadModalClose}
        confirmationButtonColor="danger"
      />
    </div>
  );
};

export default DeployedModels;
