// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';

import { useTranslation } from 'next-i18next';
import { useRouter } from 'next/router';
import { useDisclosure } from '@heroui/react';

import { fetchNamespaceMetrics } from '@/lib/app/namespaces';
import {
  fetchProfilesForServices,
  getAimServices,
  getAimClusterModels,
  resolveAIMServiceDisplay,
  undeployAim,
} from '@/lib/app/aims';
import type { AIMServiceProfile } from '@/lib/app/aims';
import { deleteWorkload } from '@/lib/app/workloads';
import { deleteModel } from '@/lib/app/models';
import {
  AIM_CANONICAL_NAME_ANNOTATION,
  AIM_MODEL_NAME_LABEL,
  FINE_TUNED_LABEL,
} from '@/types/aims';
import { useDebouncedCallback, useSystemToast } from '@amdenterpriseai/hooks';

import { displayMegabytesInGigabytes } from '@amdenterpriseai/utils/app';
import { getWorkloadStatusVariants } from '@/utils/workloads';
import { getWorkloadTypeVariants } from '@amdenterpriseai/utils/app';

import { TableColumns } from '@amdenterpriseai/types';
import { SortDirection } from '@amdenterpriseai/types';
import { ResourceType } from '@/types/enums/workloads';
import { WorkloadType } from '@amdenterpriseai/types';
import { WorkloadStatus } from '@/types/enums/workloads';
import { NamespaceWorkloadsTableField } from '@/enums';
import type { ResourceMetrics } from '@/types/namespaces';
import type { AIMService, ParsedAIM } from '@/types/aims';
import { CollectionRequestParams } from '@amdenterpriseai/types';
import { NamespaceMetricsResponse } from '@/types/namespaces';

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

import { ModelProfileSummary } from '@/components/shared/ModelProfileSummary';
import DeleteWorkloadModal from '@/components/features/workloads/DeleteWorkloadModal';
import WorkloadLogsModal from '@/components/features/workloads/WorkloadLogsModal';
import { LogSource } from '@/components/features/workloads/WorkloadLogs';
import AIMConnectModal from '@/components/features/models/AIMConnectModal';
import { useProject } from '@/contexts/ProjectContext';
import { SUBMITTER_ANNOTATION_KEY } from '../secrets/constants';

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
  const { t } = useTranslation(['projects', 'workloads', 'models']);
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
  } = useDisclosure();

  const {
    isOpen: isWorkloadLogsModalOpen,
    onOpen: onWorkloadLogsModalOpen,
    onOpenChange: onWorkloadLogsModalOpenChange,
  } = useDisclosure();

  const {
    isOpen: isConnectModalOpen,
    onOpen: onConnectModalOpen,
    onClose: onConnectModalClose,
  } = useDisclosure();

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
    useQuery<NamespaceMetricsResponse>({
      queryKey: ['namespace', namespace, 'workloads', fetchParams],
      queryFn: () => fetchNamespaceMetrics(namespace, fetchParams),
      enabled: !!namespace,
    });

  const { data: aimServices, isFetching: isAimServicesLoading } = useQuery({
    queryKey: ['namespace', namespace, 'aim-services'],
    queryFn: () => getAimServices(namespace),
    enabled: !!namespace,
  });

  const { data: parsedAIMs = [], isFetching: isParsedAIMsLoading } = useQuery({
    queryKey: ['aim-cluster-models'],
    queryFn: () => getAimClusterModels(),
    enabled: !!namespace,
  });

  const { data: aimServiceProfiles = new Map<string, AIMServiceProfile>() } =
    useQuery({
      queryKey: [
        'namespace',
        namespace,
        'aim-service-profiles',
        (aimServices ?? []).map((s) => s.id),
      ],
      queryFn: () => fetchProfilesForServices(aimServices ?? []),
      enabled: (aimServices?.length ?? 0) > 0,
    });

  // Merge profile data into items so HeroUI's TableBody sees a new array reference
  // when profiles resolve, triggering a re-render of rows.
  const tableData = useMemo((): ResourceMetrics[] => {
    const rows = namespaceMetrics?.data ?? [];
    if (!aimServices || aimServiceProfiles.size === 0) return rows;

    // TODO: This is workaround as the API doesn't return createdAt and createdBy as it still reading from DB.
    // Follow up this on https://amd.atlassian.net/browse/EAI-6063

    const aimServiceById = new Map<string, AIMService>(
      aimServices.flatMap((s) => (s.id ? [[s.id, s]] : [])),
    );

    return rows.map((item) => {
      const profile = aimServiceProfiles.get(String(item.id));
      if (!profile) return item;
      const aimService = aimServiceById.get(String(item.id));

      return {
        ...item,
        createdAt:
          item.createdAt ?? aimService?.metadata?.creationTimestamp ?? null,
        createdBy:
          item.createdBy ??
          aimService?.metadata?.annotations?.[SUBMITTER_ANNOTATION_KEY] ??
          null,
        metric: profile.metric ?? null,
        gpu: profile.gpu ?? null,
        templateGpuCount: profile.templateGpuCount ?? null,
        precision: profile.precision ?? null,
      };
    });
  }, [namespaceMetrics?.data, aimServices, aimServiceProfiles]);

  // TODO(EAI-6064): The fine-tuned branch fakes a ParsedAIM because
  // AIMConnectModal asks for one but only uses two fields off it
  // (deployedService + canonicalName). When that ticket lands and the modal
  // takes (service, canonicalName) directly, delete the fake-ParsedAIM
  // construction and pass `aimService` + canonical-name annotation
  // (`AIM_CANONICAL_NAME_ANNOTATION`) straight through.
  const aimForConnectModal = useMemo((): ParsedAIM | undefined => {
    if (
      !resourceForConnect ||
      resourceForConnect.resourceType !== ResourceType.AIM_SERVICE ||
      !aimServices
    )
      return undefined;
    const aimService = aimServices.find((s) => s.id === resourceForConnect.id);
    if (!aimService) return undefined;
    const modelRef = aimService.status?.resolvedModel?.name;

    // Cluster-scoped deployment: catalog has the parsed AIM
    const baseAim = parsedAIMs.find((a) => a.model === modelRef);
    if (baseAim) {
      return {
        ...baseAim,
        deployedService: aimService,
      };
    }

    // Fine-tuned (namespace-scoped) deployment: not in cluster catalog.
    // Read the canonical name from the AIMService annotation.
    const canonicalName =
      aimService.metadata.annotations?.[AIM_CANONICAL_NAME_ANNOTATION] ?? '';
    return {
      model: modelRef ?? '',
      imageReference: '',
      annotations: {},
      description: { short: '', full: '' },
      title:
        aimService.metadata.annotations?.[AIM_MODEL_NAME_LABEL] ??
        aimService.metadata.name,
      imageVersion: '',
      canonicalName,
      tags: [],
      status: aimService.status.status,
      workloadStatuses: [],
      isPreview: false,
      isHfTokenRequired: false,
      deployedService: aimService,
      deployedServices: [aimService],
    };
  }, [resourceForConnect, aimServices, parsedAIMs]);

  const { mutate: deleteWorkloadMutated } = useMutation({
    mutationFn: (id: string) => {
      const resource = workloadBeingSelected;
      if (!resource) {
        throw new Error('No resource selected');
      }

      if (resource.resourceType === ResourceType.AIM_SERVICE) {
        return undeployAim(namespace, id);
      } else if (resource.type === WorkloadType.FINE_TUNING) {
        return deleteModel(id, namespace);
      } else {
        return deleteWorkload(id, namespace);
      }
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
            label: t('models:aimCatalog.actions.connect.label'),
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

      if (item.status !== WorkloadStatus.DELETED) {
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
      const profileSummary = <ModelProfileSummary profile={item} t={t} />;

      if (isAimService && aimServices && parsedAIMs.length > 0) {
        const aimService = aimServices.find(
          (service) => service.id === item.id,
        );
        if (aimService) {
          const displayInfo = resolveAIMServiceDisplay(aimService, parsedAIMs);
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
        type={item.type ?? t(`common.error.misc.unknownEntity`)}
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
        total={namespaceMetrics?.total ?? 0}
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
          logSource={
            workloadBeingSelected.resourceType === ResourceType.AIM_SERVICE
              ? LogSource.AIM
              : LogSource.WORKLOAD
          }
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
        aim={aimForConnectModal}
        onConfirmAction={(aim) => {
          const serviceId = aim.deployedService?.id;
          if (serviceId)
            window.open(projectUrl(`/chat?workload=${serviceId}`), '_blank');
          onConnectModalClose();
          setResourceForConnect(undefined);
        }}
      />
    </div>
  );
};

export default NamespaceWorkloadsTable;
