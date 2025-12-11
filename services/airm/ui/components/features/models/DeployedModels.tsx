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
import { useTranslation } from 'next-i18next';

import useSystemToast from '@/hooks/useSystemToast';

import { getAims } from '@/services/app/aims';
import { getModels } from '@/services/app/models';
import { deleteWorkload, listWorkloads } from '@/services/app/workloads';

import { getFilteredData } from '@/utils/app/data-table';
import getWorkloadStatusVariants from '@/utils/app/workloads-status-variants';
import getWorkloadTypeVariants from '@/utils/app/workloads-type-variants';

import { TableColumns } from '@/types/data-table/clientside-table';
import { FilterComponentType } from '@/types/enums/filters';
import { SortDirection } from '@/types/enums/sort-direction';
import { WorkloadStatus, WorkloadType } from '@/types/enums/workloads';
import { WorkloadsTableFields } from '@/types/enums/workloads-table-fields';
import { ClientSideDataFilter, FilterValueMap } from '@/types/filters';
import { Model } from '@/types/models';
import { Workload } from '@/types/workloads';
import { Aim } from '@/types/aims';

import { ConfirmationModal } from '@/components/shared/Confirmation/ConfirmationModal';
import ClientSideDataTable from '@/components/shared/DataTable/ClientSideDataTable';
import {
  ChipDisplay,
  DateDisplay,
  NoDataDisplay,
  StatusDisplay,
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

const DeployedModels: React.FC = ({}) => {
  const { t } = useTranslation(['workloads', 'models', 'common']);
  const { toast } = useSystemToast();
  const router = useRouter();
  const { activeProject } = useProject();

  const [filters, setFilters] = useState<ClientSideDataFilter<Workload>[]>(
    convertFilterValueMap({
      status: defaultStatusSet,
    }),
  );

  const [workloadBeingSelected, setWorkloadBeingSelected] = useState<
    Workload | undefined
  >(undefined);

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
      return listWorkloads(activeProject!);
    },
    refetchInterval: 30000, // Refetch every 30 seconds
    enabled: !!activeProject,
  });

  const workloads = useMemo(() => {
    if (!allWorkloads) return [];
    const inferenceWorkloads = allWorkloads.filter(
      (w) => w.type === WorkloadType.INFERENCE,
    );
    const filteredWorkloads = getFilteredData(inferenceWorkloads, filters);
    return filteredWorkloads;
  }, [allWorkloads, filters]);

  const hasAimWorkloads = useMemo(
    () => workloads.some((w) => w.aimId),
    [workloads],
  );

  const hasModelWorkloads = useMemo(
    () => workloads.some((w) => w.modelId),
    [workloads],
  );

  const { data: aims = [] } = useQuery({
    queryKey: ['project', activeProject, 'aim-catalog'],
    queryFn: () => getAims(activeProject!),
    enabled: !!activeProject && hasAimWorkloads,
  });

  const { data: models = [] } = useQuery<Model[]>({
    queryKey: ['project', activeProject, 'custom-models'],
    queryFn: () => getModels(activeProject!),
    enabled: !!activeProject && hasModelWorkloads,
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

  const aimsMap = useMemo(() => {
    const map = new Map<string, Aim>();
    aims.forEach((aim) => {
      if (aim.workload?.id) {
        map.set(aim.workload.id, aim);
      }
    });
    return map;
  }, [aims]);

  const modelsMap = useMemo(() => {
    const map = new Map<string, Model>();
    models.forEach((model) => {
      if (model.id) {
        map.set(model.id, model);
      }
    });
    return map;
  }, [models]);

  const customRenderers: Partial<
    Record<WorkloadsTableFields, (item: Workload) => React.ReactNode | string>
  > = {
    [WorkloadsTableFields.DISPLAY_NAME]: (item) => item.displayName,
    [WorkloadsTableFields.CANONICAL_NAME]: (item) => {
      const model = item.modelId ? modelsMap.get(item.modelId) : undefined;
      if (model?.canonicalName) {
        return model.canonicalName;
      }
      const aim = aimsMap.get(item.id);
      return (
        aim?.canonicalName ||
        item.userInputs?.canonicalName || <NoDataDisplay />
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
      status: {
        name: 'status',
        label: t('list.filters.status.label'),
        placeholder: t('list.filters.status.label'),
        type: FilterComponentType.DROPDOWN,
        defaultSelectedValues: defaultStatusSet.map(String),
        fields: [
          WorkloadStatus.ADDED,
          WorkloadStatus.PENDING,
          WorkloadStatus.RUNNING,
          WorkloadStatus.TERMINATED,
          WorkloadStatus.COMPLETE,
          WorkloadStatus.FAILED,
          WorkloadStatus.DELETING,
          WorkloadStatus.DELETE_FAILED,
          WorkloadStatus.DELETED,
        ].map((status) => ({
          props: {
            description: t(`status.${status}`),
            showDivider: status === WorkloadStatus.DELETE_FAILED,
          },
          key: String(status),
          label: t(`status.${status}`),
        })),
      },
    }),
    [t],
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
        isLoading={isWorkloadsLoading}
        isFetching={isWorkloadsRefetching}
        idKey={'id'}
      />
      <ConfirmationModal
        isOpen={isDeleteWorkloadModalOpen}
        onConfirm={() => deleteWorkloadMutated(workloadBeingSelected?.id || '')}
        description={t(
          'customModels.list.actions.undeploy.confirmation.description',
          {
            ns: 'models',
            name: workloadBeingSelected?.displayName || '',
          },
        )}
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
