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
import {
  AIM_CANONICAL_NAME_ANNOTATION,
  AIM_MODEL_NAME_LABEL,
  AIM_MODEL_WORKLOAD_ID_LABEL,
  FINE_TUNED_LABEL,
} from '@/types/aims';
import { AIMModelResponse } from '@/types/models';
import { deleteWorkload, listWorkloads } from '@/lib/app/workloads';

import { getFilteredData } from '@amdenterpriseai/utils/app';
import { getWorkloadStatusVariants } from '@/utils/workloads';
import { getWorkloadTypeVariants } from '@amdenterpriseai/utils/app';

import { TableColumns } from '@amdenterpriseai/types';
import { FilterComponentType } from '@amdenterpriseai/types';
import { SortDirection } from '@amdenterpriseai/types';
import { WorkloadType } from '@amdenterpriseai/types';
import { WorkloadStatus } from '@/types/enums/workloads';
import { WorkloadsTableFields } from '@/types/enums/workloads-table-fields';
import { ClientSideDataFilter, FilterValueMap } from '@amdenterpriseai/types';
import { Model } from '@/types/models';
import { Workload } from '@/types/workloads';

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
  fetchProfilesForServices,
  getAimClusterModels,
  getAimServices,
  mapAIMServiceStatusToWorkloadStatus,
  resolveAIMServiceDisplay,
  undeployAim,
} from '@/lib/app/aims';
import type { AIMServiceProfile } from '@/lib/app/aims';
import { ModelProfileSummary } from '@/components/shared/ModelProfileSummary';
import { AIMService, ParsedAIM } from '@/types/aims';
import { SUBMITTER_ANNOTATION_KEY } from '@/components/features/secrets/constants';
import AIMConnectModal from './AIMConnectModal';

const defaultStatusSet = [
  WorkloadStatus.PENDING,
  WorkloadStatus.STARTING,
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
  const { activeProject, projectPath, projectUrl } = useProject();

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
    data: allAimServices = [],
    isLoading: isAimServicesLoading,
    isRefetching: isAimServicesRefetching,
    refetch: refetchAimServices,
  } = useQuery<AIMService[]>({
    queryKey: ['project', activeProject, 'aim-services'],
    queryFn: () => getAimServices(activeProject!),
    refetchInterval: 30000,
    enabled: !!activeProject,
  });

  const { data: aimServiceProfiles = new Map<string, AIMServiceProfile>() } =
    useQuery({
      queryKey: [
        'project',
        activeProject,
        'aim-service-profiles',
        allAimServices.map((s) => s.id),
      ],
      queryFn: () => fetchProfilesForServices(allAimServices),
      enabled: allAimServices.length > 0,
    });

  // Merge AIM Services with Workloads to create an aggregated list for the table
  const allDeployments = useMemo(() => {
    if (!allWorkloads || !allAimServices) return [];
    const aimWorkloads: Workload[] = allAimServices.map((aim) => ({
      id: aim.id,
      displayName: aim.metadata.name,
      name: aim.metadata.name,
      type: WorkloadType.INFERENCE,
      status: mapAIMServiceStatusToWorkloadStatus(aim.status.status),
      createdAt: aim.metadata.creationTimestamp,
      createdBy: aim.metadata.annotations[SUBMITTER_ANNOTATION_KEY],
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

  const hasFinetuningWorkloads = useMemo(
    () => workloads.some((w) => w.type === WorkloadType.FINE_TUNING),
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
    queryFn: async () => {
      const data = await getModels(activeProject!);
      return data.map((item: AIMModelResponse) => ({
        id: item.metadata.labels?.[AIM_MODEL_WORKLOAD_ID_LABEL],
        name: item.metadata.name,
        canonicalName: item.spec?.modelSources?.[0]?.modelId || '',
        resourceName: item.metadata.name,
      }));
    },
    enabled: !!activeProject && hasFinetuningWorkloads,
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

  // TODO(EAI-6064): The fine-tuned branch below fakes a ParsedAIM because
  // AIMConnectModal asks for one but only uses two fields off it
  // (deployedService + canonicalName). When that ticket lands and the modal
  // takes (service, canonicalName) directly, delete the fake-ParsedAIM
  // construction and pass `matchingService` + canonical-name annotation
  // (`AIM_CANONICAL_NAME_ANNOTATION`) straight through.
  const aimForConnectModal = useMemo((): ParsedAIM | undefined => {
    if (!workloadForConnect?.aimId || !allAimServices) return undefined;
    const matchingService = allAimServices.find(
      (s) => s.id === workloadForConnect.id,
    );

    // Cluster-scoped deployment: catalog has the parsed AIM
    const baseAim = aims?.find((a) => a.model === workloadForConnect.aimId);
    if (baseAim) {
      return {
        ...baseAim,
        deployedService: matchingService ?? baseAim.deployedService,
      };
    }

    // Fine-tuned (namespace-scoped) deployment: not in cluster catalog.
    // Read the canonical name from the AIMService annotation.
    if (!matchingService) return undefined;
    const canonicalName =
      matchingService.metadata.annotations?.[AIM_CANONICAL_NAME_ANNOTATION] ??
      '';
    return {
      model: workloadForConnect.aimId,
      imageReference: '',
      annotations: {},
      description: { short: '', full: '' },
      title:
        matchingService.metadata.annotations?.[AIM_MODEL_NAME_LABEL] ??
        matchingService.metadata.name,
      imageVersion: '',
      canonicalName,
      tags: [],
      status: matchingService.status.status,
      workloadStatuses: [],
      isPreview: false,
      isHfTokenRequired: false,
      deployedService: matchingService,
      deployedServices: [matchingService],
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
      const aimService =
        item.aimId && allAimServices
          ? allAimServices.find((service) => service.id === item.id)
          : undefined;
      const profile = aimService
        ? aimServiceProfiles.get(String(aimService.id))
        : undefined;
      const profileSummary = (
        <ModelProfileSummary profile={profile ?? null} t={t} />
      );

      if (item.aimId && allAimServices && aims) {
        if (aimService) {
          const displayInfo = resolveAIMServiceDisplay(aimService, aims);
          // Fine-tuned: show the user-given name (title); cluster catalog: show canonical + version.
          const isFineTuned =
            aimService.metadata.labels?.[FINE_TUNED_LABEL] === 'true';
          const displayName = isFineTuned
            ? displayInfo.title
            : `${displayInfo.canonicalName} ${displayInfo.imageVersion ? `(${displayInfo.imageVersion})` : ''}`.trim();
          return (
            <div className="flex flex-col gap-1">
              <span>{displayName}</span>
              {profileSummary}
            </div>
          );
        }
      }
      const displayName = item.displayName ?? item.name;
      if (!displayName) {
        return <NoDataDisplay />;
      }
      return (
        <div className="flex flex-col gap-1">
          <span>{displayName}</span>
          {profileSummary}
        </div>
      );
    },
    [WorkloadsTableFields.CANONICAL_NAME]: (item) => {
      const model = modelsMap.get(item.id);
      if (model?.canonicalName) {
        return model.canonicalName;
      }
      const aim = aims.find((a) => a.model === item.aimId);
      if (aim?.canonicalName) {
        return aim.canonicalName;
      }
      // Fine-tuned deployments aren't in the cluster catalog; the canonical
      // lives on the AIMService annotation.
      const aimService = allAimServices?.find((s) => s.id === item.id);
      const annotationCanonical =
        aimService?.metadata.annotations?.[AIM_CANONICAL_NAME_ANNOTATION];
      return (
        annotationCanonical ||
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
            pathname: projectPath(`/aims/${w.id}`),
            query: { ref: router.asPath },
          });
        } else {
          router.push({
            pathname: projectPath(`/workloads/${w.id}`),
            query: { ref: router.asPath },
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
          window.open(projectUrl(`/chat?workload=${item.id}`), '_blank');
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
          WorkloadStatus.STARTING,
          WorkloadStatus.RUNNING,
          WorkloadStatus.COMPLETE,
          WorkloadStatus.FAILED,
          WorkloadStatus.UNKNOWN,
          WorkloadStatus.DELETING,
          WorkloadStatus.DELETED,
        ].map((status) => ({
          props: {
            description: t(`workloads:status.${status}`),
            showDivider: status === WorkloadStatus.DELETING,
          },
          key: String(status),
          label: t(`workloads:status.${status}`),
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
          if (serviceId)
            window.open(projectUrl(`/chat?workload=${serviceId}`), '_blank');
          onConnectModalClose();
          setWorkloadForConnect(undefined);
        }}
      />
    </div>
  );
};

export default DeployedModels;
