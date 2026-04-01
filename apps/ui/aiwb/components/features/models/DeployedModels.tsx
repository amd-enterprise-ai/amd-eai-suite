// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useDisclosure } from '@heroui/react';
import {
  IconExternalLink,
  IconEye,
  IconLink,
  IconMessage,
  IconRocketOff,
} from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';

import { useRouter } from 'next/router';
import { useTranslation } from 'next-i18next';

import { useSystemToast } from '@amdenterpriseai/hooks';

import { getModels } from '@/lib/app/models';
import { deleteWorkload, listWorkloads } from '@/lib/app/workloads';

import { getFilteredData } from '@amdenterpriseai/utils/app';
import { getWorkloadStatusVariants } from '@amdenterpriseai/utils/app';
import { getWorkloadTypeVariants } from '@amdenterpriseai/utils/app';

import { TableColumns } from '@amdenterpriseai/types';
import { FilterComponentType } from '@amdenterpriseai/types';
import { SortDirection } from '@amdenterpriseai/types';
import { WorkloadStatus, WorkloadType } from '@amdenterpriseai/types';
import { WorkloadsTableFields } from '@amdenterpriseai/types';
import { ClientSideDataFilter, FilterValueMap } from '@amdenterpriseai/types';
import { Model } from '@amdenterpriseai/types';
import { Workload } from '@amdenterpriseai/types';

import { ConfirmationModal } from '@amdenterpriseai/components';
import { ClientSideDataTable } from '@amdenterpriseai/components';
import {
  ChipDisplay,
  DateDisplay,
  NoDataDisplay,
  StatusDisplay,
} from '@amdenterpriseai/components';
import { ActionsToolbar } from '@amdenterpriseai/components';

import { useProject } from '@/contexts/ProjectContext';
import {
  getAimClusterModels,
  getAimServices,
  mapAIMServiceStatusToWorkloadStatus,
  resolveAIMServiceDisplay,
  undeployAim,
} from '@/lib/app/aims';
import { ParsedAIM } from '@/types/aims';
import AIMConnectModal from './AIMConnectModal';

const defaultStatusSet = [
  WorkloadStatus.PENDING,
  WorkloadStatus.RUNNING,
  WorkloadStatus.FAILED,
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
  if (filters?.status && filters.status.length > 0) {
    newFilters.push({
      field: 'status',
      values: filters.status,
    });
  }
  if (filters?.type && filters.type.length > 0) {
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
  const [workloadForConnect, setWorkloadForConnect] = useState<
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
      if (!activeProject) return [];

      const response = await listWorkloads(activeProject, {
        type: [WorkloadType.INFERENCE],
      });
      return response.data;
    },
    refetchInterval: 30000,
    enabled: !!activeProject,
  });

  const {
    data: allAimServices,
    isLoading: isAimServicesLoading,
    isRefetching: isAimServicesRefetching,
    refetch: refetchAimServices,
  } = useQuery({
    queryKey: ['project', activeProject, 'aim-services'],
    queryFn: async () => {
      if (!activeProject) return [];
      const response = await getAimServices(activeProject);
      return response;
    },
    refetchInterval: 30000,
    enabled: !!activeProject,
  });

  // Merge AIM Services with Workloads to create an aggregated list for the table
  const allDeployments = useMemo(() => {
    if (!allWorkloads || !allAimServices) return [];
    const aimWorkloads: Workload[] = allAimServices.map((aim) => ({
      id: aim.id,
      displayName: aim.metadata.name,
      name: aim.resourceName,
      type: WorkloadType.INFERENCE,
      status: mapAIMServiceStatusToWorkloadStatus(aim.status.status),
      createdAt: aim.metadata.creationTimestamp,
      createdBy: aim.metadata.annotations.airmSilogenAiSubmitter,
      updatedAt: aim.metadata.creationTimestamp,
      aimId: aim.status.resolvedModel?.name,
    })) as Workload[];
    return [...allWorkloads, ...aimWorkloads];
  }, [allWorkloads, allAimServices]);

  const workloads = useMemo(() => {
    if (!allDeployments) return [];
    const filteredWorkloads = getFilteredData(allDeployments, filters);
    return filteredWorkloads;
  }, [allDeployments, filters]);

  const hasAimWorkloads = useMemo(
    () => workloads.some((w) => w.aimId),
    [workloads],
  );

  const hasModelWorkloads = useMemo(
    () => workloads.some((w) => w.modelId),
    [workloads],
  );

  const {
    data: aims = [],
    isLoading: isAimsLoading,
    isRefetching: isAimsRefetching,
    refetch: refetchAims,
  } = useQuery<ParsedAIM[]>({
    queryKey: ['project', activeProject, 'aim-catalog'],
    queryFn: () => getAimClusterModels(activeProject!),
    enabled: !!activeProject && hasAimWorkloads,
  });

  const {
    data: models = [],
    isLoading: isModelsLoading,
    isRefetching: isModelsRefetching,
    refetch: refetchModels,
  } = useQuery<Model[]>({
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
      mutationFn: (id: string) => deleteWorkload(id, activeProject!),
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
    mutate: deleteAimServiceMutated,
    isPending: isAIMServiceDeletePending,
  } = useMutation({
    mutationFn: (id: string) => undeployAim(activeProject!, id),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['project', activeProject, 'aim-services'],
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

  const {
    isOpen: isConnectModalOpen,
    onOpen: onConnectModalOpen,
    onClose: onConnectModalClose,
  } = useDisclosure();

  const aimForConnectModal = useMemo((): ParsedAIM | undefined => {
    if (!workloadForConnect?.aimId || !aims || !allAimServices)
      return undefined;
    const baseAim = aims.find((a) => a.model === workloadForConnect.aimId);
    const matchingService = allAimServices.find(
      (s) => s.id === workloadForConnect.id,
    );
    if (!baseAim) return undefined;
    return {
      ...baseAim,
      deployedService: matchingService ?? baseAim.deployedService,
    };
  }, [workloadForConnect, aims, allAimServices]);

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
    [WorkloadsTableFields.DISPLAY_NAME]: (item) => {
      if (item.aimId && allAimServices && aims) {
        const aimService = allAimServices.find(
          (service) => service.id === item.id,
        );
        if (aimService) {
          const displayInfo = resolveAIMServiceDisplay(aimService, aims);
          const metricLabel = t(
            `models:performanceMetrics.values.${displayInfo.metric}`,
          );
          return `${displayInfo.canonicalName} ${displayInfo.imageVersion ? `(${displayInfo.imageVersion})` : ''} (${metricLabel})`;
        }
      }
      return item.displayName ?? item.name ?? '-';
    },
    [WorkloadsTableFields.CANONICAL_NAME]: (item) => {
      const model = item.modelId ? modelsMap.get(item.modelId) : undefined;
      if (model?.canonicalName) {
        return model.canonicalName;
      }
      const aim = aims.find((a) => a.model === item.aimId);
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
        if (w.aimId) {
          router.push({
            pathname: `/aims/${w.id}`,
            search: `ref=${router.asPath}`,
          });
        } else {
          router.push({
            pathname: `/workloads/${w.id}`,
            search: `ref=${router.asPath}`,
          });
        }
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
      if (item.aimId) {
        actionsList.push({
          key: 'connect',
          label: t('aimCatalog.actions.connect.label', { ns: 'models' }),
          startContent: <IconLink />,
          onPress: (w: Workload) => {
            setWorkloadForConnect(w);
            onConnectModalOpen();
          },
        });
      }
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
          WorkloadStatus.PENDING,
          WorkloadStatus.RUNNING,
          WorkloadStatus.COMPLETE,
          WorkloadStatus.FAILED,
          WorkloadStatus.UNKNOWN,
          WorkloadStatus.DELETING,
          WorkloadStatus.DELETED,
        ].map((status) => ({
          props: {
            description: t(`status.${status}`),
            showDivider: status === WorkloadStatus.DELETING,
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
    refetchModels();
    refetchAims();
    refetchAimServices();
  };

  const isDataLoading =
    isWorkloadsLoading ||
    isModelsLoading ||
    isAimsLoading ||
    isAimServicesLoading;

  const isFetching =
    isWorkloadsRefetching ||
    isModelsRefetching ||
    isAimsRefetching ||
    isAimServicesRefetching;

  return (
    <div className="flex flex-col w-full" data-testid="deployed-models">
      <ActionsToolbar
        filterConfig={filterConfig}
        onFilterChange={handleFilterChange}
        isRefreshing={isFetching}
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
        isLoading={isDataLoading}
        isFetching={isFetching}
        idKey={'id'}
      />
      <ConfirmationModal
        isOpen={isDeleteWorkloadModalOpen}
        onConfirm={() =>
          workloadBeingSelected?.aimId
            ? deleteAimServiceMutated(workloadBeingSelected?.id || '')
            : deleteWorkloadMutated(workloadBeingSelected?.id || '')
        }
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
        loading={isAIMServiceDeletePending || isDeletePending}
        onClose={onDeleteWorkloadModalClose}
        confirmationButtonColor="danger"
      />
      <AIMConnectModal
        isOpen={isConnectModalOpen}
        onOpenChange={(isOpen) => {
          if (!isOpen) {
            onConnectModalClose();
            setWorkloadForConnect(undefined);
          }
        }}
        aim={aimForConnectModal}
        onConfirmAction={(aim) => {
          const serviceId = aim.deployedService?.id;
          if (serviceId) window.open(`/chat?workload=${serviceId}`, '_blank');
          onConnectModalClose();
          setWorkloadForConnect(undefined);
        }}
      />
    </div>
  );
};

export default DeployedModels;
