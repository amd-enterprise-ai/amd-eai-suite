// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import { useDisclosure } from '@heroui/react';
import {
  IconAffiliate,
  IconEye,
  IconRocket,
  IconTrash,
} from '@tabler/icons-react';
import { useQuery } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { useTranslation } from 'next-i18next';

import { useSystemToast } from '@amdenterpriseai/hooks';

import { getModels } from '@/lib/app/models';
import { listWorkloads } from '@/lib/app/workloads';

import { getFilteredData } from '@amdenterpriseai/utils/app';
import { getModelStatusVariants } from '@/lib/app/models-status-variants';

import { ActionButton } from '@amdenterpriseai/components';
import { CatalogItem } from '@amdenterpriseai/types';
import { ActionItem, TableColumns } from '@amdenterpriseai/types';
import { CatalogItemCategory, CatalogItemType } from '@amdenterpriseai/types';
import { FilterComponentType } from '@amdenterpriseai/types';
import { ModelsTableField } from '@amdenterpriseai/types';
import { SortDirection } from '@amdenterpriseai/types';
import { WorkloadStatus, WorkloadType } from '@amdenterpriseai/types';
import { ClientSideDataFilter, FilterValueMap } from '@amdenterpriseai/types';
import { Model, ModelOnboardingStatus } from '@amdenterpriseai/types';

import ModelDetailsModal from '@/components/features/models/ModelDetailsModal';
import { ClientSideDataTable } from '@amdenterpriseai/components';
import { DateDisplay, StatusDisplay } from '@amdenterpriseai/components';
import { ActionsToolbar } from '@amdenterpriseai/components';

import { useProject } from '@/contexts/ProjectContext';
import { useRouter } from 'next/router';

interface CustomModelsProps {
  onOpenDeployModal: (catalogItem: CatalogItem) => void;
  onOpenFinetuneModal: (model?: Model) => void;
  onOpenDeleteModal: (model: Model) => void;
  finetunableModels: string[] | undefined;
}

const defaultStatusSet = [
  ModelOnboardingStatus.READY,
  ModelOnboardingStatus.PENDING,
  ModelOnboardingStatus.FAILED,
];

const convertFilterValueMap = (
  filters: FilterValueMap,
): ClientSideDataFilter<Model>[] => {
  const newFilters: ClientSideDataFilter<Model>[] = [];
  if (filters?.search) {
    newFilters.push({
      field: 'name',
      values: filters.search,
    });
  }
  if (filters?.status && filters.status.length > 0) {
    newFilters.push({
      field: 'onboardingStatus',
      values: filters.status,
    });
  }
  return newFilters;
};

const CustomModels: React.FC<CustomModelsProps> = ({
  onOpenDeployModal,
  onOpenFinetuneModal,
  onOpenDeleteModal,
  finetunableModels,
}) => {
  const { t } = useTranslation('models');
  const { t: tCustomModels } = useTranslation('models', {
    keyPrefix: 'customModels',
  });
  const router = useRouter();
  const { toast } = useSystemToast();
  const { activeProject } = useProject();

  const [filters, setFilters] = useState<ClientSideDataFilter<Model>[]>(
    convertFilterValueMap({
      status: defaultStatusSet,
    }),
  );

  const {
    data: models,
    isLoading: isModelsLoading,
    isRefetching: isModelsRefetching,
    refetch: refetchModels,
    error: modelsError,
    dataUpdatedAt: modelsDataUpdatedAt,
  } = useQuery<Model[]>({
    queryKey: ['project', activeProject, 'models', 'custom'],
    queryFn: async () => {
      return await getModels(activeProject!);
    },
    refetchInterval: 30000, // Refetch every 30 seconds
    enabled: !!activeProject,
  });

  const {
    data: workloads,
    isLoading: isWorkloadsLoading,
    refetch: refetchWorkloads,
    dataUpdatedAt: workloadsDataUpdatedAt,
  } = useQuery({
    queryKey: ['project', activeProject, 'workloads'],
    queryFn: async () => {
      if (!activeProject) return [];

      const response = await listWorkloads(activeProject, {
        type: [WorkloadType.INFERENCE, WorkloadType.FINE_TUNING],
      });
      return response.data;
    },
    refetchInterval: 30000, // Refetch every 30 seconds
    enabled: !!activeProject,
  });

  const dataUpdatedAt = modelsDataUpdatedAt || workloadsDataUpdatedAt;

  const refetchModelsAndWorkloads = useCallback(async () => {
    await Promise.all([refetchModels(), refetchWorkloads()]);
  }, [refetchModels, refetchWorkloads]);

  const workloadsCount = useMemo(() => {
    const workloadsCountByModelId = new Map<string, number>();
    if (workloads) {
      workloads.forEach((workload) => {
        if (
          workload.modelId &&
          (workload.status == WorkloadStatus.PENDING ||
            workload.status == WorkloadStatus.RUNNING)
        ) {
          workloadsCountByModelId.set(
            workload.modelId,
            (workloadsCountByModelId.get(workload.modelId) || 0) + 1,
          );
        }
      });
    }
    return workloadsCountByModelId;
  }, [workloads]);

  const filteredModels = useMemo(() => {
    if (!models) return [];

    const filteredModels = getFilteredData(models, filters);
    return filteredModels.reduce<
      (Model & { [ModelsTableField.WORKLOADS]: number })[]
    >((result, model) => {
      result.push({
        ...model,
        [ModelsTableField.WORKLOADS]: model.id
          ? workloadsCount.get(model.id) || 0
          : 0,
      });

      return result;
    }, []);
  }, [models, filters, workloadsCount]);

  const {
    isOpen: isModelDetailsModalOpen,
    onOpen: onModelDetailsModalOpen,
    onOpenChange: onModelDetailsModalOpenChange,
  } = useDisclosure();

  const [modelBeingSelected, setModelBeingSelected] = useState<
    Model | undefined
  >(undefined);

  const statusFilterItems = useMemo(
    () => [
      {
        key: ModelOnboardingStatus.PENDING,
        label: t(`status.${ModelOnboardingStatus.PENDING}`),
      },
      {
        key: ModelOnboardingStatus.READY,
        label: t(`status.${ModelOnboardingStatus.READY}`),
      },
      {
        key: ModelOnboardingStatus.FAILED,
        label: t(`status.${ModelOnboardingStatus.FAILED}`),
      },
    ],
    [t],
  );

  useEffect(() => {
    if (modelsError) {
      toast.error(
        t('notifications.refresh.error', {
          error: String(modelsError.message),
        }),
      );
    }
  }, [modelsError, toast, t]);

  const columns: TableColumns<ModelsTableField> = [
    {
      key: ModelsTableField.NAME,
      sortable: true,
    },
    {
      key: ModelsTableField.CANONICAL_NAME,
      sortable: true,
    },
    {
      key: ModelsTableField.CREATED_BY,
      sortable: true,
    },
    {
      key: ModelsTableField.CREATED_AT,
      sortable: true,
    },
    {
      key: ModelsTableField.ONBOARDING_STATUS,
      sortable: true,
    },
    {
      key: ModelsTableField.WORKLOADS,
      sortable: true,
    },
  ];

  const actions = (item: Model) => {
    const actionsList: ActionItem<Model>[] = [
      {
        key: 'details',
        color: 'default',
        startContent: <IconEye />,
        onPress: (m: Model) => {
          setModelBeingSelected(m);
          const finetuningWorkload = workloads?.find(
            (workload) =>
              workload.modelId === m.id &&
              workload.type === WorkloadType.FINE_TUNING,
          );
          if (finetuningWorkload) {
            router.push({
              pathname: `/workloads/${finetuningWorkload.id}`,
              search: `ref=${router.asPath}`,
            });
          } else {
            onModelDetailsModalOpen();
          }
        },
        label: t('customModels.list.actions.details.label'),
      },
    ];

    if (item.onboardingStatus === ModelOnboardingStatus.READY) {
      actionsList.push({
        key: 'deploy',
        color: 'default',
        startContent: <IconRocket />,
        onPress: (model: Model) => {
          const catalogItem: CatalogItem = {
            id: model.id,
            name: model.name,
            displayName: model.name,
            slug: model.canonicalName,
            description: model.name,
            longDescription: `${model.name} - ${model.canonicalName}`,
            type: CatalogItemType.INFERENCE,
            category: CatalogItemCategory.INFERENCE,
            createdAt: model.createdAt,
            tags: [],
            available: model.onboardingStatus === ModelOnboardingStatus.READY,
            workloadsCount: 0,
            workloads: [],
          };
          onOpenDeployModal(catalogItem);
        },
        label: t('customModels.list.actions.deploy.label'),
      });
    }

    if (
      item.onboardingStatus === ModelOnboardingStatus.READY &&
      finetunableModels?.includes(item.canonicalName)
    )
      actionsList.push({
        key: 'finetune',
        color: 'default',
        startContent: <IconAffiliate />,
        onPress: (m: Model) => {
          onOpenFinetuneModal(m);
        },
        label: t('customModels.list.actions.finetune.label'),
      });

    actionsList.push({
      key: 'delete',
      color: 'danger',
      startContent: <IconTrash />,
      onPress: (m: Model) => {
        onOpenDeleteModal(m);
      },
      label: t('customModels.list.actions.delete.label'),
    });
    return actionsList;
  };

  const customRenderers: Partial<
    Record<ModelsTableField, (item: Model) => React.ReactNode | string>
  > = {
    [ModelsTableField.CREATED_AT]: (item: Model) => (
      <DateDisplay date={item[ModelsTableField.CREATED_AT]} />
    ),
    [ModelsTableField.ONBOARDING_STATUS]: (item: Model) => (
      <StatusDisplay
        type={item[ModelsTableField.ONBOARDING_STATUS] as ModelOnboardingStatus}
        variants={getModelStatusVariants(t)}
      />
    ),
  };

  const filterConfig = useMemo(
    () => ({
      search: {
        name: 'search',
        label: t('customModels.list.filters.search.placeholder'),
        placeholder: t('customModels.list.filters.search.placeholder'),
        type: FilterComponentType.TEXT,
      },
      status: {
        name: 'status',
        label: t('customModels.list.filters.status.label'),
        placeholder: t('customModels.list.filters.status.placeholder'),
        type: FilterComponentType.DROPDOWN,
        defaultSelectedValues: defaultStatusSet,
        fields: statusFilterItems,
      },
    }),
    [t, statusFilterItems],
  );

  const handleFilterChange = (filters: FilterValueMap) => {
    const newFilters: ClientSideDataFilter<Model>[] =
      convertFilterValueMap(filters);
    setFilters(newFilters);
  };

  return (
    <div data-testid="custom-models" className="flex flex-col w-full">
      <ActionsToolbar
        filterConfig={filterConfig}
        onFilterChange={handleFilterChange}
        onRefresh={refetchModelsAndWorkloads}
        updatedTimestamp={dataUpdatedAt}
        isRefreshing={isModelsLoading || isWorkloadsLoading}
        endContent={
          <ActionButton
            primary
            isDisabled={isModelsLoading || isWorkloadsLoading}
            onPress={() => onOpenFinetuneModal(undefined)}
            icon={<IconAffiliate size={16} stroke={3} />}
          >
            {t('customModels.list.actions.finetune.title')}
          </ActionButton>
        }
      />

      <ClientSideDataTable
        data={filteredModels}
        columns={columns}
        className="flex-1 overflow-y-auto"
        defaultSortByField={ModelsTableField.CREATED_AT}
        defaultSortDirection={SortDirection.DESC}
        customRenderers={
          customRenderers as Record<string, (item: unknown) => React.ReactNode>
        }
        isLoading={isModelsLoading || isWorkloadsLoading}
        isFetching={isModelsRefetching}
        translation={tCustomModels}
        idKey={'id' as never}
        rowActions={actions}
      />

      <ModelDetailsModal
        onOpenChange={onModelDetailsModalOpenChange}
        isOpen={isModelDetailsModalOpen}
        model={modelBeingSelected}
      />
    </div>
  );
};

export default CustomModels;
