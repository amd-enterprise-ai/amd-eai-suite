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
  getAimServices,
  getAimClusterModels,
  resolveAIMServiceDisplay,
  undeployAim,
} from '@/lib/app/aims';
import { deleteWorkload } from '@/lib/app/workloads';
import { useDebouncedCallback, useSystemToast } from '@amdenterpriseai/hooks';

import { displayMegabytesInGigabytes } from '@amdenterpriseai/utils/app';
import { getWorkloadStatusVariants } from '@amdenterpriseai/utils/app';
import { getWorkloadTypeVariants } from '@amdenterpriseai/utils/app';

import { TableColumns } from '@amdenterpriseai/types';
import { SortDirection } from '@amdenterpriseai/types';
import { ResourceType } from '@amdenterpriseai/types';
import { WorkloadStatus, WorkloadType } from '@amdenterpriseai/types';
import { NamespaceWorkloadsTableField } from '../../../enums';
import type {
  ResourceMetrics,
  NamespaceMetricsResponse,
} from '../../../types/namespaces';
import type { ParsedAIM } from '@/types/aims';
import { CollectionRequestParams } from '@amdenterpriseai/types';

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

import DeleteWorkloadModal from '@/components/features/workloads/DeleteWorkloadModal';
import WorkloadLogsModal from '@/components/features/workloads/WorkloadLogsModal';
import { LogSource } from '@/components/features/workloads/WorkloadLogs';
import AIMConnectModal from '@/components/features/models/AIMConnectModal';

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
      queryKey: ['namespace', namespace, 'metrics', fetchParams],
      queryFn: () => fetchNamespaceMetrics(namespace, fetchParams),
      enabled: !!namespace,
    });

  const { data: aimServices, isFetching: isAimServicesLoading } = useQuery({
    queryKey: ['namespace', namespace, 'aim-services'],
    queryFn: () => getAimServices(namespace),
    enabled: !!namespace,
  });

  const { data: parsedAIMs = [], isFetching: isParsedAIMsLoading } = useQuery({
    queryKey: ['aim-cluster-models', namespace],
    queryFn: () => getAimClusterModels(namespace),
    enabled: !!namespace,
  });

  const aimForConnectModal = useMemo((): ParsedAIM | undefined => {
    if (
      !resourceForConnect ||
      resourceForConnect.resourceType !== ResourceType.AIM_SERVICE ||
      !aimServices ||
      !parsedAIMs.length
    )
      return undefined;
    const aimService = aimServices.find((s) => s.id === resourceForConnect.id);
    if (!aimService) return undefined;
    const modelRef = aimService.status?.resolvedModel?.name;
    const baseAim = parsedAIMs.find(
      (a) => a.model === modelRef || a.resourceName === modelRef,
    );
    if (!baseAim) return undefined;
    return {
      ...baseAim,
      deployedService: aimService,
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
      } else {
        return deleteWorkload(id, namespace);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['namespace', namespace, 'metrics'],
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
                ? `/aims/${w.id}`
                : `/workloads/${w.id}`;

            router.push({
              pathname,
              search: `ref=${router.asPath}`,
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
            window.open(`/chat?workload=${item.id}`, '_blank');
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
      if (
        item.resourceType === ResourceType.AIM_SERVICE &&
        aimServices &&
        parsedAIMs
      ) {
        const aimService = aimServices.find(
          (service) => service.id === item.id,
        );
        if (aimService) {
          const displayInfo = resolveAIMServiceDisplay(aimService, parsedAIMs);
          const metricLabel = t(
            `models:performanceMetrics.values.${displayInfo.metric}`,
          );
          return `${displayInfo.canonicalName} ${displayInfo.imageVersion ? `(${displayInfo.imageVersion})` : ''} (${metricLabel})`;
        }
      }
      return item.displayName ?? item.name ?? <NoDataDisplay />;
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
        data={namespaceMetrics?.data ?? []}
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
          if (serviceId) window.open(`/chat?workload=${serviceId}`, '_blank');
          onConnectModalClose();
          setResourceForConnect(undefined);
        }}
      />
    </div>
  );
};

export default NamespaceWorkloadsTable;
