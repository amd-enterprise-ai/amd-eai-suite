// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

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

import { useOverlayState, useSystemToast } from '@amdenterpriseai/hooks';

import { listAllProjectFineTunedModels } from '@/lib/app/models';
import {
  AIM_CANONICAL_NAME_ANNOTATION,
  AIM_DISPLAY_NAME_ANNOTATION,
  AIM_MODEL_WORKLOAD_ID_LABEL,
  AIMModel,
  FINE_TUNED_LABEL,
  NAMESPACE_AIM_MODEL_LABEL,
} from '@/types/aims';
import { listAllWorkloads } from '@/lib/app/workloads';

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

import {
  ActionsToolbar,
  ChipDisplay,
  ClientSideDataTable,
  ConfirmationModal,
  DateDisplay,
  NoDataDisplay,
  StatusDisplay,
} from '@amdenterpriseai/components';

import { useProject } from '@/contexts/ProjectContext';
import {
  aimParser,
  mapAIMServiceStatusToWorkloadStatus,
  resolveAIMServiceDisplay,
  resolveBaseModelSource,
} from '@/lib/app/aims';
import { useProfileSpecsForServices } from '@/hooks/useProfileSpecsForServices';
import {
  deleteInferenceDeployment,
  listAllInferenceDeployments,
} from '@/lib/app/inference';
import { useInferenceModelsByName } from '@/hooks/useInferenceModelsByName';
import {
  ModelProfileSummary,
  toProfileSummaryFields,
} from '@/components/shared/ModelProfileSummary';
import { AIMService } from '@/types/aims';
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
  const { t } = useTranslation(['workloads', 'common']);
  const { t: tModels } = useTranslation('models');
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

      return await listAllWorkloads(activeProject, {
        type: [WorkloadType.INFERENCE],
      });
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
    queryFn: () => listAllInferenceDeployments(activeProject!),
    refetchInterval: 30000,
    enabled: !!activeProject,
  });

  // Merge AIM Services with Workloads to create an aggregated list for the table
  const allDeployments = useMemo(() => {
    if (!allWorkloads || !allAimServices) return [];
    // Filter out AIM services with null ids — they cannot be de-duplicated
    // against workloads and would silently collapse into one row under the null key.
    const aimWorkloads: Workload[] = allAimServices
      .filter((aim): aim is typeof aim & { id: string } => aim.id !== null)
      .map((aim) => ({
        id: aim.id,
        // Prefer the user-entered deploy name over the K8s resource name.
        displayName:
          aim.metadata.annotations?.[AIM_DISPLAY_NAME_ANNOTATION] ??
          aim.metadata.name,
        name: aim.metadata.name,
        type: WorkloadType.INFERENCE,
        status: mapAIMServiceStatusToWorkloadStatus(aim.status.status),
        createdAt: aim.metadata.creationTimestamp,
        createdBy: aim.metadata.annotations[SUBMITTER_ANNOTATION_KEY],
        updatedAt: aim.metadata.creationTimestamp,
        aimId: aim.spec.model?.name,
      }));

    // listWorkloads and AIM services can refer to the same deployment id.
    // Prefer AIM-derived fields for overlaps to avoid duplicate rows/keys.
    const deploymentsById = new Map<string, Workload>();
    allWorkloads.forEach((workload) => {
      deploymentsById.set(workload.id, workload);
    });

    aimWorkloads.forEach((aimWorkload) => {
      const existing = deploymentsById.get(aimWorkload.id);
      if (existing) {
        deploymentsById.set(aimWorkload.id, {
          ...existing,
          ...aimWorkload,
          // Spreading aimWorkload above would overwrite the workload row's
          // resolved name with the AIM name; restore the canonical values.
          displayName: existing.displayName,
          name: existing.name,
        });
        return;
      }

      deploymentsById.set(aimWorkload.id, aimWorkload);
    });

    return Array.from(deploymentsById.values());
  }, [allWorkloads, allAimServices]);

  const workloads = useMemo(() => {
    if (!allDeployments) return [];
    const filteredWorkloads = getFilteredData(allDeployments, filters);
    return filteredWorkloads;
  }, [allDeployments, filters]);

  const hasFinetuningWorkloads = useMemo(
    () => workloads.some((w) => w.type === WorkloadType.FINE_TUNING),
    [workloads],
  );

  const hasAimWorkloads = workloads.some((w) => w.aimId);

  // Cluster-catalog models are only needed to enrich the display of cluster-scoped AIM
  // services. Namespace-scoped AIMModel services (fine-tuned and custom-imported) aren't
  // in that catalog — resolveAIMServiceDisplay already falls back to their annotations,
  // so we skip those names.
  const clusterAimNames = useMemo(
    () =>
      allAimServices
        .filter(
          (s) =>
            s.metadata.labels?.[FINE_TUNED_LABEL] !== 'true' &&
            s.metadata.labels?.[NAMESPACE_AIM_MODEL_LABEL] !== 'true',
        )
        .map((s) => s.spec.model?.name)
        .filter((name): name is string => !!name),
    [allAimServices],
  );
  const {
    byName: clusterAimsByName,
    isLoading: isAimsLoading,
    isFetching: isAimsFetching,
  } = useInferenceModelsByName(clusterAimNames);
  const aims = useMemo(
    () => Array.from(clusterAimsByName.values()).map((m) => aimParser(m)),
    [clusterAimsByName],
  );

  // Raw FT model CRs — kept around so we can derive both the simplified
  // `Model[]` shape consumed downstream AND each model's `status.aimId` for
  // the per-aimId profile fetch.
  const {
    data: fineTunedModelCrs = [],
    isLoading: isModelsLoading,
    isRefetching: isModelsRefetching,
    refetch: refetchModels,
  } = useQuery<AIMModel[]>({
    queryKey: ['project', activeProject, 'fine-tuned-models'],
    queryFn: () => listAllProjectFineTunedModels(activeProject!),
    enabled: !!activeProject && (hasFinetuningWorkloads || hasAimWorkloads),
  });

  const models: Model[] = useMemo(
    () =>
      fineTunedModelCrs.map((item) => ({
        id: item.metadata.labels?.[AIM_MODEL_WORKLOAD_ID_LABEL],
        name: item.metadata.name,
        canonicalName: resolveBaseModelSource(item)?.modelId || '',
        resourceName: item.metadata.name,
      })),
    [fineTunedModelCrs],
  );

  // Profile lookup map for the row-level summary (metric / gpu / precision).
  // Wait for both upstream model fetches to settle before deriving aimIds —
  // otherwise each per-name model landing would change the array and
  // trigger a superseding profile fetch (waterfall).
  const isUpstreamLoading = isAimsLoading || isModelsLoading;
  const aimIds = isUpstreamLoading
    ? []
    : [
        ...Array.from(clusterAimsByName.values()).map((m) => m.status?.aimId),
        ...fineTunedModelCrs.map((m) => m.status?.aimId),
      ].filter((id): id is string => !!id);
  const { specByName: profileSpecByName } = useProfileSpecsForServices({
    aimIds,
    project: activeProject,
  });

  // BaseDataTable caches cell renders keyed by row reference (see the
  // comment in `apps/ui/shared/components/src/DataTable/BaseDataTable.tsx`).
  // The DISPLAY_NAME renderer closes over `profileSpecByName`, so when the
  // profile fetch resolves we mint new row references to force the table to
  // re-invoke the renderer with the now-populated map.
  const tableRows = useMemo(
    () => workloads.map((w) => ({ ...w })),
    [workloads, profileSpecByName],
  );

  useEffect(() => {
    if (workloadsError) {
      toast.error(
        t('notifications.refresh.error', {
          error: String(workloadsError.message),
        }),
      );
    }
  }, [workloadsError, toast, t]);

  const { mutate: deleteAimServiceMutated, isPending: isDeletePending } =
    useMutation({
      mutationFn: (id: string) => deleteInferenceDeployment(activeProject!, id),
      onSuccess: () => {
        queryClient.invalidateQueries({
          queryKey: ['project', activeProject, 'aim-services'],
        });
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
  } = useOverlayState();

  const {
    isOpen: isConnectModalOpen,
    onOpen: onConnectModalOpen,
    onClose: onConnectModalClose,
  } = useOverlayState();

  const connectInfo = useMemo(() => {
    if (!workloadForConnect?.aimId || !allAimServices) return undefined;
    const service = allAimServices.find((s) => s.id === workloadForConnect.id);
    if (!service) return undefined;
    const modelName = service.status?.resolvedModel?.name;
    return {
      serviceId: service.id ?? undefined,
      endpoints: service.endpoints,
      modelName,
    };
  }, [workloadForConnect, allAimServices]);

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
        ? toProfileSummaryFields(aimService, profileSpecByName)
        : undefined;
      const profileSummary = (
        <ModelProfileSummary profile={profile ?? null} t={tModels} />
      );

      if (item.aimId && allAimServices && aims) {
        if (aimService) {
          const displayInfo = resolveAIMServiceDisplay(aimService, aims);
          const canonicalName =
            `${displayInfo.canonicalName} ${displayInfo.imageVersion ? `(${displayInfo.imageVersion})` : ''}`.trim();
          // Prefer the API display name; fall back to canonical + version when
          // the API only echoes the K8s resource name (displayName === name).
          const displayName =
            item.displayName && item.displayName !== item.name
              ? item.displayName
              : canonicalName;
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
    refetchAimServices();
    // Cluster-catalog models are fetched via per-name useQueries entries; nuking
    // the shared key invalidates every entry so a refetch picks up changes.
    queryClient.invalidateQueries({ queryKey: ['inferenceModel'] });
  };

  const isDataLoading =
    isWorkloadsLoading ||
    isModelsLoading ||
    isAimsLoading ||
    isAimServicesLoading;

  const isFetching =
    isWorkloadsRefetching ||
    isModelsRefetching ||
    isAimServicesRefetching ||
    isAimsFetching;

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
        data={tableRows}
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
          deleteAimServiceMutated(workloadBeingSelected?.id || '')
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
        loading={isDeletePending}
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
        serviceId={connectInfo?.serviceId}
        endpoints={connectInfo?.endpoints}
        modelName={connectInfo?.modelName}
        onChatRequested={(serviceId) => {
          window.open(projectUrl(`/chat?workload=${serviceId}`), '_blank');
          onConnectModalClose();
          setWorkloadForConnect(undefined);
        }}
      />
    </div>
  );
};

export default DeployedModels;
