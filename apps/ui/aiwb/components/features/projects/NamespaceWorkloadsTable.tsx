// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';

import { useTranslation } from 'next-i18next';
import { useRouter } from 'next/router';
import { fetchProjectWorkloadMetrics } from '@/lib/app/projects';
import { aimParser, resolveAIMServiceDisplay } from '@/lib/app/aims';
import {
  deleteInferenceDeployment,
  listAllInferenceDeployments,
} from '@/lib/app/inference';
import { useInferenceModelsByName } from '@/hooks/useInferenceModelsByName';
import { deleteWorkspace } from '@/lib/app/workloads';
import {
  cancelFineTuningJob,
  listAllProjectFineTunedModels,
} from '@/lib/app/models';
import { useProfileSpecsForServices } from '@/hooks/useProfileSpecsForServices';
import {
  AIMService,
  FINE_TUNED_LABEL,
  NAMESPACE_AIM_MODEL_LABEL,
} from '@/types/aims';

import { displayMegabytesInGigabytes } from '@amdenterpriseai/utils/app';
import { getWorkloadStatusVariants } from '@/utils/workloads';
import { getWorkloadTypeVariants } from '@amdenterpriseai/utils/app';

import { TableColumns } from '@amdenterpriseai/types';
import { SortDirection } from '@amdenterpriseai/types';
import { ResourceType } from '@/types/enums/workloads';
import { WorkloadType } from '@amdenterpriseai/types';
import { WorkloadStatus } from '@/types/enums/workloads';
import { NamespaceWorkloadsTableField } from '@/enums';
import type { ResourceMetrics } from '@/types/projects';
import {
  useDebouncedCallback,
  useOverlayState,
  useSystemToast,
} from '@amdenterpriseai/hooks';
import { CollectionRequestParams } from '@amdenterpriseai/types';
import { WorkloadMetricsResponse } from '@/types/projects';

import {
  ChipDisplay,
  DateDisplay,
  NoDataDisplay,
  ServerSideDataTable,
  StatusDisplay,
} from '@amdenterpriseai/components';
import { ActionItem } from '@amdenterpriseai/types';

import {
  IconEye,
  IconFileText,
  IconLink,
  IconMessage,
  IconTrash,
} from '@tabler/icons-react';

import {
  ModelProfileSummary,
  toProfileSummaryFields,
} from '@/components/shared/ModelProfileSummary';
import DeleteWorkloadModal from '@/components/features/workloads/DeleteWorkloadModal';
import WorkloadLogsModal from '@/components/features/workloads/WorkloadLogsModal';
import AIMConnectModal from '@/components/features/models/AIMConnectModal';
import { useProject } from '@/contexts/ProjectContext';
import { SUBMITTER_ANNOTATION_KEY } from '@/components/features/secrets/constants';

interface Props {
  namespace: string;
}

const columns: TableColumns<NamespaceWorkloadsTableField | null> = [
  {
    key: NamespaceWorkloadsTableField.NAME,
    sortable: true,
  },
  {
    key: NamespaceWorkloadsTableField.TYPE,
    sortable: true,
  },
  { key: NamespaceWorkloadsTableField.STATUS, sortable: true },
  { key: NamespaceWorkloadsTableField.GPUS },
  { key: NamespaceWorkloadsTableField.VRAM },
  { key: NamespaceWorkloadsTableField.CREATED_AT, sortable: true },
  { key: NamespaceWorkloadsTableField.CREATED_BY, sortable: true },
];

const API_REQUEST_DEFAULTS: CollectionRequestParams<ResourceMetrics> = {
  page: 1,
  pageSize: 20,
  sort: [
    {
      field: 'createdAt' as keyof ResourceMetrics,
      direction: SortDirection.DESC,
    },
  ],
  filter: [],
};

export const NamespaceWorkloadsTable: React.FC<Props> = ({ namespace }) => {
  const { t } = useTranslation(['projects', 'workloads', 'common']);
  const { t: tModels } = useTranslation('models');
  const { t: workloadsT } = useTranslation('workloads');
  const router = useRouter();
  const { projectPath, projectUrl } = useProject();
  const { toast } = useSystemToast();
  const queryClient = useQueryClient();

  const [tableParams, setTableParams] =
    useState<CollectionRequestParams<ResourceMetrics>>(API_REQUEST_DEFAULTS);
  const [workloadBeingSelected, setWorkloadBeingSelected] = useState<
    ResourceMetrics | undefined
  >(undefined);
  const [resourceForConnect, setResourceForConnect] = useState<
    ResourceMetrics | undefined
  >(undefined);

  const {
    isOpen: isDeleteWorkloadModalOpen,
    onOpen: onDeleteWorkloadModalOpen,
    onOpenChange: onDeleteWorkloadModalOpenChange,
  } = useOverlayState();

  const {
    isOpen: isWorkloadLogsModalOpen,
    onOpen: onWorkloadLogsModalOpen,
    onOpenChange: onWorkloadLogsModalOpenChange,
  } = useOverlayState();

  const {
    isOpen: isConnectModalOpen,
    onOpen: onConnectModalOpen,
    onClose: onConnectModalClose,
  } = useOverlayState();

  const fetchParams = useMemo(() => {
    const sortField = tableParams.sort?.[0]?.field as string | undefined;
    const sortDirection = tableParams.sort?.[0]?.direction;

    return {
      page: tableParams.page,
      pageSize: tableParams.pageSize,
      sortBy: sortField,
      sortOrder: sortDirection,
    };
  }, [tableParams]);

  const { data: namespaceMetrics, isFetching: isNamespaceMetricsLoading } =
    useQuery<WorkloadMetricsResponse>({
      queryKey: ['namespace', namespace, 'workloads', fetchParams],
      queryFn: () => fetchProjectWorkloadMetrics(namespace, fetchParams),
      enabled: !!namespace,
    });

  const { data: aimServices, isFetching: isAimServicesLoading } = useQuery({
    queryKey: ['namespace', namespace, 'aim-services'],
    queryFn: () => listAllInferenceDeployments(namespace),
    enabled: !!namespace,
  });

  // Cluster-catalog models are only needed to enrich the display for cluster-scoped AIM
  // services. Namespace-scoped AIMModel services (fine-tuned and custom-imported) aren't
  // in that catalog — resolveAIMServiceDisplay already falls back to their annotations,
  // so we skip those names.
  const clusterAimNames = useMemo(
    () =>
      (aimServices ?? [])
        .filter(
          (s) =>
            s.metadata.labels?.[FINE_TUNED_LABEL] !== 'true' &&
            s.metadata.labels?.[NAMESPACE_AIM_MODEL_LABEL] !== 'true',
        )
        .map((s) => s.spec.model?.name)
        .filter((name): name is string => !!name),
    [aimServices],
  );
  const { byName: clusterAimsByName, isLoading: isParsedAIMsLoading } =
    useInferenceModelsByName(clusterAimNames);
  const parsedAIMs = useMemo(
    () => Array.from(clusterAimsByName.values()).map((m) => aimParser(m)),
    [clusterAimsByName],
  );

  // Fine-tuned AIMModels in the project — needed so we can derive their
  // status.aimId and fetch only the namespace AIMProfiles actually
  // referenced by displayed FT services.
  const { data: fineTunedModels = [], isLoading: isFineTunedLoading } =
    useQuery({
      queryKey: ['project', namespace, 'fine-tuned-models'],
      queryFn: () => listAllProjectFineTunedModels(namespace),
      enabled: !!namespace,
      staleTime: 5 * 60_000,
    });

  // Profile lookup map built from per-aimId fetches against the cluster
  // and project profile endpoints. Wait for both upstream model fetches to
  // settle before deriving aimIds — otherwise each per-name model landing
  // would trigger a superseding profile fetch.
  const isUpstreamLoading = isParsedAIMsLoading || isFineTunedLoading;
  const aimIds = isUpstreamLoading
    ? []
    : [
        ...Array.from(clusterAimsByName.values()).map((m) => m.status?.aimId),
        ...fineTunedModels.map((m) => m.status?.aimId),
      ].filter((id): id is string => !!id);
  const { specByName: profileSpecByName } = useProfileSpecsForServices({
    aimIds,
    project: namespace,
  });

  // Merge resolved profile spec into table rows so HeroUI's TableBody sees a
  // new array reference when AIM services arrive and rows can render
  // hardware details.
  const tableData = useMemo((): ResourceMetrics[] => {
    const rows = namespaceMetrics?.data ?? [];
    if (!aimServices || aimServices.length === 0) return rows;

    // TODO: This is workaround as the API doesn't return createdAt and createdBy as it still reading from DB.
    // Follow up this on https://amd.atlassian.net/browse/EAI-6063

    const aimServiceById = new Map<string, AIMService>(
      aimServices.flatMap((s) => (s.id ? [[s.id, s]] : [])),
    );

    return rows.map((item) => {
      const aimService = aimServiceById.get(String(item.id));
      if (!aimService) return item;
      const profile = toProfileSummaryFields(aimService, profileSpecByName);

      return {
        ...item,
        createdAt:
          item.createdAt ?? aimService?.metadata?.creationTimestamp ?? null,
        createdBy:
          item.createdBy ??
          aimService?.metadata?.annotations?.[SUBMITTER_ANNOTATION_KEY] ??
          null,
        metric: profile?.metric ?? null,
        gpu: profile?.gpu ?? null,
        templateGpuCount: profile?.templateGpuCount ?? null,
        acceleratorType: profile?.acceleratorType ?? null,
        precision: profile?.precision ?? null,
      };
    });
  }, [namespaceMetrics?.data, aimServices, profileSpecByName]);

  const connectInfo = useMemo(() => {
    if (
      !resourceForConnect ||
      resourceForConnect.resourceType !== ResourceType.AIM_SERVICE ||
      !aimServices
    )
      return undefined;
    const service = aimServices.find((s) => s.id === resourceForConnect.id);
    if (!service) return undefined;
    const modelName = service.status?.resolvedModel?.name;
    return {
      serviceId: service.id ?? undefined,
      endpoints: service.endpoints,
      modelName,
    };
  }, [resourceForConnect, aimServices]);

  const { mutate: deleteWorkloadMutated } = useMutation({
    mutationFn: (id: string) => {
      const resource = workloadBeingSelected;
      if (!resource) {
        throw new Error('No resource selected');
      }

      if (resource.resourceType === ResourceType.AIM_SERVICE) {
        return deleteInferenceDeployment(namespace, id);
      } else if (resource.type === WorkloadType.FINE_TUNING) {
        return cancelFineTuningJob(id, namespace);
      } else if (resource.type === WorkloadType.WORKSPACE) {
        return deleteWorkspace(namespace, id);
      }
      // Generic /workloads DELETE was removed in EAI-6313 — deletion is now
      // capability-specific. MODEL_DOWNLOAD/CUSTOM rows have no owning
      // capability surface yet, so the UI must not offer delete for them.
      throw new Error(
        `No delete capability for workload type ${resource.type}`,
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['namespace', namespace, 'workloads'],
      });
      queryClient.invalidateQueries({
        queryKey: ['namespace', namespace, 'stats'],
      });
      toast.success(t('workloads:list.actions.delete.notification.success'));
    },
    onError: (_) => {
      toast.error(t('workloads:list.actions.delete.notification.error'));
    },
  });

  const rowActions = useMemo(
    () => (item: ResourceMetrics) => {
      const actionsList: ActionItem<ResourceMetrics>[] = [];

      if (item.type !== WorkloadType.CUSTOM) {
        actionsList.push({
          key: 'details',
          label: t('workloads:list.actions.details.label'),
          startContent: <IconEye />,
          onPress: (w: ResourceMetrics) => {
            const pathname =
              w.resourceType === ResourceType.AIM_SERVICE
                ? projectPath(`/aims/${w.id}`)
                : projectPath(`/workloads/${w.id}`);

            router.push({
              pathname,
              query: { ref: router.asPath },
            });
          },
        });
      }

      if (
        item.type === WorkloadType.INFERENCE &&
        item.status === WorkloadStatus.RUNNING
      ) {
        actionsList.push({
          key: 'chat',
          label: t('workloads:list.actions.chat.label'),
          startContent: <IconMessage />,
          onPress: () => {
            window.open(projectUrl(`/chat?workload=${item.id}`), '_blank');
          },
        });
        if (item.resourceType === ResourceType.AIM_SERVICE) {
          actionsList.push({
            key: 'connect',
            label: tModels('aimCatalog.actions.connect.label'),
            startContent: <IconLink />,
            onPress: (w: ResourceMetrics) => {
              setResourceForConnect(w);
              onConnectModalOpen();
            },
          });
        }
      }

      actionsList.push({
        key: 'logs',
        label: t('workloads:list.actions.logs.label'),
        startContent: <IconFileText />,
        onPress: (w: ResourceMetrics) => {
          setWorkloadBeingSelected(w);
          onWorkloadLogsModalOpen();
        },
      });

      // The delete mutation can only dispatch to capability-specific endpoints
      // (AIM service / fine-tuning / workspace). MODEL_DOWNLOAD/CUSTOM and any
      // unrecognized row type have no owning capability surface, so the action
      // is filtered out rather than letting the user click into a thrown error.
      const canDelete =
        item.status !== WorkloadStatus.DELETED &&
        (item.resourceType === ResourceType.AIM_SERVICE ||
          item.type === WorkloadType.FINE_TUNING ||
          item.type === WorkloadType.WORKSPACE);

      if (canDelete) {
        actionsList.push({
          key: 'delete',
          label: t('workloads:list.actions.delete.label'),
          color: 'danger',
          startContent: <IconTrash />,
          onPress: (w: ResourceMetrics) => {
            setWorkloadBeingSelected(w);
            onDeleteWorkloadModalOpen();
          },
        });
      }

      return actionsList;
    },
    [
      t,
      router,
      onWorkloadLogsModalOpen,
      onDeleteWorkloadModalOpen,
      onConnectModalOpen,
    ],
  );

  const handleTableParamsChange = useDebouncedCallback(
    (params: CollectionRequestParams<ResourceMetrics>) => {
      setTableParams(params);
    },
    100,
  );

  const customRenderers: Partial<
    Record<
      NamespaceWorkloadsTableField,
      (item: ResourceMetrics) => React.ReactNode | string
    >
  > = {
    [NamespaceWorkloadsTableField.VRAM]: (item) =>
      item.vram !== null ? (
        displayMegabytesInGigabytes(item.vram)
      ) : (
        <NoDataDisplay />
      ),
    [NamespaceWorkloadsTableField.CREATED_AT]: (item) => {
      if (item.createdAt) {
        return <DateDisplay date={item.createdAt} />;
      }
      return <NoDataDisplay />;
    },
    [NamespaceWorkloadsTableField.NAME]: (item) => {
      const isAimService = item.resourceType === ResourceType.AIM_SERVICE;
      const profileSummary = <ModelProfileSummary profile={item} t={tModels} />;

      if (isAimService && aimServices && parsedAIMs.length > 0) {
        const aimService = aimServices.find(
          (service) => service.id === item.id,
        );
        if (aimService) {
          const displayInfo = resolveAIMServiceDisplay(aimService, parsedAIMs);
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
      return (
        <div className="flex flex-col gap-1">
          {displayName ? <span>{displayName}</span> : <NoDataDisplay />}
          {profileSummary}
        </div>
      );
    },
    [NamespaceWorkloadsTableField.STATUS]: (item) => (
      <StatusDisplay
        type={item.status}
        variants={getWorkloadStatusVariants(workloadsT)}
      />
    ),
    [NamespaceWorkloadsTableField.TYPE]: (item) => (
      <ChipDisplay
        type={item.type ?? t('common:error.misc.unknownEntity')}
        variants={getWorkloadTypeVariants(workloadsT)}
      />
    ),
    [NamespaceWorkloadsTableField.GPUS]: (item) =>
      item.gpuCount ?? <NoDataDisplay />,
    [NamespaceWorkloadsTableField.CREATED_BY]: (item) =>
      item.createdBy ?? <NoDataDisplay />,
  };

  return (
    <div>
      <ServerSideDataTable
        filters={[]}
        handleDataRequest={handleTableParamsChange}
        total={namespaceMetrics?.pagination.total ?? 0}
        data={tableData}
        columns={columns}
        customRenderers={customRenderers}
        defaultSortByField={NamespaceWorkloadsTableField.CREATED_AT}
        defaultSortDirection={SortDirection.DESC}
        rowActions={rowActions}
        translation={t}
        idKey="id"
        translationKeyPrefix="workloads"
        isLoading={
          isNamespaceMetricsLoading ||
          isAimServicesLoading ||
          isParsedAIMsLoading
        }
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
          namespace={namespace}
        />
      )}
      <AIMConnectModal
        isOpen={isConnectModalOpen}
        onOpenChange={(isOpen) => {
          if (!isOpen) {
            onConnectModalClose();
            setResourceForConnect(undefined);
          }
        }}
        serviceId={connectInfo?.serviceId}
        endpoints={connectInfo?.endpoints}
        modelName={connectInfo?.modelName}
        onChatRequested={(serviceId) => {
          window.open(projectUrl(`/chat?workload=${serviceId}`), '_blank');
          onConnectModalClose();
          setResourceForConnect(undefined);
        }}
      />
    </div>
  );
};

export default NamespaceWorkloadsTable;
