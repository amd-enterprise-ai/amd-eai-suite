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

import useSystemToast from '@/hooks/useSystemToast';

import { getModels } from '@/services/app/models';
import { listWorkloads } from '@/services/app/workloads';

import { getFilteredData } from '@/utils/app/data-table';
import getModelStatusVariants from '@/utils/app/models-status-variants';

import { ActionButton } from '@/components/shared/Buttons/ActionButton';
import { CatalogItem } from '@/types/catalog';
import { ActionItem, TableColumns } from '@/types/data-table/clientside-table';
import { CatalogItemCategory, CatalogItemType } from '@/types/enums/catalog';
import { FilterComponentType } from '@/types/enums/filters';
import { ModelsTableField } from '@/types/enums/models-table-fields';
import { SortDirection } from '@/types/enums/sort-direction';
import { WorkloadStatus, WorkloadType } from '@/types/enums/workloads';
import { ClientSideDataFilter, FilterValueMap } from '@/types/filters';
import { Model, ModelOnboardingStatus } from '@/types/models';

import ModelDetailsModal from '@/components/features/models/ModelDetailsModal';
import ClientSideDataTable from '@/components/shared/DataTable/ClientSideDataTable';
import {
  DateDisplay,
  StatusDisplay,
} from '@/components/shared/DataTable/CustomRenderers';
import { ActionsToolbar } from '@/components/shared/Toolbar/ActionsToolbar';

import { useProject } from '@/contexts/ProjectContext';

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
  if (filters?.status) {
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
    queryKey: ['project', activeProject, 'custom-models'],
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
      return await listWorkloads(activeProject!, {
        type: [WorkloadType.INFERENCE],
        status: [WorkloadStatus.RUNNING],
      });
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
        if (workload.modelId) {
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
          onModelDetailsModalOpen();
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

    if (finetunableModels?.includes(item.canonicalName))
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
