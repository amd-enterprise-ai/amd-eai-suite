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
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { useTranslation } from 'next-i18next';

import { useSystemToast } from '@amdenterpriseai/hooks';

import {
  deleteModel,
  finetuneModel,
  getFinetunableModels,
  getModels,
} from '@/lib/app/models';
import {
  AIM_MODEL_NAME_LABEL,
  AIM_MODEL_WORKLOAD_ID_LABEL,
  AIMService,
  AIMStatus,
} from '@/types/aims';
import { AIMModelResponse, ModelFinetuneParams } from '@/types/models';
import { deleteWorkload, listWorkloads } from '@/lib/app/workloads';
import { getAimServices } from '@/lib/app/aims';
import { APIRequestError } from '@amdenterpriseai/utils/app';

import { getFilteredData } from '@amdenterpriseai/utils/app';
import { getWorkloadStatusVariants } from '@/utils/workloads';

import { ActionButton } from '@amdenterpriseai/components';
import { ActionItem, TableColumns } from '@amdenterpriseai/types';
import { FilterComponentType } from '@amdenterpriseai/types';
import { ModelsTableField } from '@/types/enums/models-table-fields';
import { SortDirection } from '@amdenterpriseai/types';
import { WorkloadType } from '@amdenterpriseai/types';
import { WorkloadStatus } from '@/types/enums/workloads';
import { ClientSideDataFilter, FilterValueMap } from '@amdenterpriseai/types';
import { FinetunableModel, Model, ModelOnboardingStatus } from '@/types/models';

import DeleteModelModal from '@/components/features/models/DeleteModelModal';
import { DeployFinetuneAIMDrawer } from '@/components/features/models/DeployFinetuneAIMDrawer';
import FinetuneDrawer from '@/components/features/models/FinetuneDrawer';
import ModelDetailsModal from '@/components/features/models/ModelDetailsModal';
import DeleteWorkloadModal from '@/components/features/workloads/DeleteWorkloadModal';
import { ClientSideDataTable } from '@amdenterpriseai/components';
import { StatusDisplay } from '@amdenterpriseai/components';
import { ActionsToolbar } from '@amdenterpriseai/components';

import { useProject } from '@/contexts/ProjectContext';
import { useRouter } from 'next/router';
import { Workload } from '@/types/workloads';

type ModelRow = Model & { source: 'model' | 'workload' };

const defaultStatusSet = [
  WorkloadStatus.PENDING,
  WorkloadStatus.RUNNING,
  WorkloadStatus.COMPLETE,
  WorkloadStatus.FAILED,
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
      field: 'status',
      values: filters.status,
    });
  }
  return newFilters;
};

const CustomModels = () => {
  const { t } = useTranslation('models');
  const { t: tCustomModels } = useTranslation('models', {
    keyPrefix: 'customModels',
  });
  const { t: tWorkloads } = useTranslation('workloads');
  const router = useRouter();
  const queryClient = useQueryClient();
  const { toast } = useSystemToast();
  const { activeProject, projectPath } = useProject();

  const [modelForDeletion, setModelForDeletion] = useState<Model | undefined>(
    undefined,
  );
  const [workloadForDeletion, setWorkloadForDeletion] = useState<
    Workload | undefined
  >(undefined);
  const [hasActiveDeployments, setHasActiveDeployments] = useState(false);
  const [modelForAIMDeploy, setModelForAIMDeploy] = useState<Model | null>(
    null,
  );
  const [modelToFinetune, setModelToFinetune] = useState<Model | undefined>(
    undefined,
  );

  const finetuneDisclosure = useDisclosure();

  const { data: finetunableModels } = useQuery({
    queryKey: ['models', 'finetunable'],
    queryFn: (): Promise<FinetunableModel[]> => getFinetunableModels(),
  });

  const deleteModelDisclosure = useDisclosure();
  const deleteWorkloadDisclosure = useDisclosure();

  const [filters, setFilters] = useState<ClientSideDataFilter<Model>[]>(
    convertFilterValueMap({
      status: defaultStatusSet,
    }),
  );

  const {
    data: rawModels,
    isLoading: isModelsLoading,
    isRefetching: isModelsRefetching,
    refetch: refetchModels,
    error: modelsError,
    dataUpdatedAt: modelsDataUpdatedAt,
  } = useQuery<AIMModelResponse[]>({
    queryKey: ['project', activeProject, 'models', 'custom'],
    queryFn: () => getModels(activeProject!),
    refetchInterval: 30000,
    enabled: !!activeProject,
  });

  const models: ModelRow[] = useMemo(
    () =>
      (rawModels ?? []).map((item) => {
        const labels = item.metadata.labels ?? {};
        return {
          id: labels[AIM_MODEL_WORKLOAD_ID_LABEL],
          name: labels[AIM_MODEL_NAME_LABEL] || item.metadata.name,
          canonicalName: item.spec?.modelSources?.[0]?.modelId || '',
          resourceName: item.metadata.name,
          source: 'model' as const,
          status: (() => {
            switch (item.status?.status as AIMStatus | string) {
              case AIMStatus.READY:
                return WorkloadStatus.COMPLETE;
              case AIMStatus.FAILED:
              case AIMStatus.DEGRADED:
                return WorkloadStatus.FAILED;
              default:
                return WorkloadStatus.PENDING;
            }
          })(),
          workloadId: labels[AIM_MODEL_WORKLOAD_ID_LABEL],
          createdAt: item.metadata?.creationTimestamp,
        };
      }),
    [rawModels],
  );

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
        // No need to show the deleted workloads in the table.
        status: [
          WorkloadStatus.PENDING,
          WorkloadStatus.STARTING,
          WorkloadStatus.RUNNING,
          WorkloadStatus.COMPLETE,
          WorkloadStatus.FAILED,
        ],
      });
      return response.data;
    },
    refetchInterval: 30000, // Refetch every 30 seconds
    enabled: !!activeProject,
  });

  const {
    data: aimServices = [],
    refetch: refetchAimServices,
    dataUpdatedAt: aimServicesDataUpdatedAt,
  } = useQuery<AIMService[]>({
    queryKey: ['project', activeProject, 'aim-services'],
    queryFn: () => getAimServices(activeProject!),
    refetchInterval: 30000,
    enabled: !!activeProject,
  });

  const dataUpdatedAt =
    modelsDataUpdatedAt || workloadsDataUpdatedAt || aimServicesDataUpdatedAt;

  const refetchModelsAndWorkloads = useCallback(async () => {
    await Promise.all([
      refetchModels(),
      refetchWorkloads(),
      refetchAimServices(),
    ]);
  }, [refetchModels, refetchWorkloads, refetchAimServices]);

  const deleteModelMutation = useMutation({
    mutationFn: async (variables: { name: string; force?: boolean }) => {
      if (!activeProject) {
        throw new Error('No active project selected');
      }
      await deleteModel(variables.name, activeProject, variables.force);
    },
    onSuccess: () => {
      setHasActiveDeployments(false);
      queryClient.invalidateQueries({
        queryKey: ['project', activeProject, 'models'],
      });
      queryClient.invalidateQueries({
        queryKey: ['project', activeProject, 'workloads'],
      });
      toast.success(
        t(
          'customModels.list.actions.delete.notification.success',
          'Model deleted successfully',
        ),
      );
      deleteModelDisclosure.onClose();
    },
    onError: (error: unknown) => {
      if (error instanceof APIRequestError && error.statusCode === 409) {
        setHasActiveDeployments(true);
        return;
      }
      deleteModelDisclosure.onClose();
      const message =
        error instanceof APIRequestError ? error.message : undefined;
      toast.error(
        message ||
          t(
            'customModels.list.actions.delete.notification.error',
            'Error deleting model',
          ),
      );
      console.error('Error deleting model:', error);
    },
  });

  const deleteWorkloadMutation = useMutation({
    mutationFn: async (id: string) => {
      if (!activeProject) {
        throw new Error('No active project selected');
      }
      await deleteWorkload(id, activeProject);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['project', activeProject, 'models'],
      });
      queryClient.invalidateQueries({
        queryKey: ['project', activeProject, 'workloads'],
      });
      toast.success(
        t(
          'customModels.list.actions.delete.workloadNotification.success',
          'Workload deleted successfully',
        ),
      );
      deleteWorkloadDisclosure.onClose();
    },
    onError: (error: unknown) => {
      const message =
        error instanceof APIRequestError ? error.message : undefined;
      toast.error(
        message ||
          t(
            'customModels.list.actions.delete.notification.error',
            'Error deleting workload',
          ),
      );
      console.error('Error deleting workload:', error);
    },
  });

  const handleOpenDeleteModal = useCallback(
    (item: ModelRow) => {
      if (item.source === 'model') {
        setModelForDeletion(item);
        setHasActiveDeployments(false);
        deleteModelDisclosure.onOpen();
      } else {
        setWorkloadForDeletion({
          id: item.workloadId!,
          name: item.resourceName || item.name,
          displayName: item.canonicalName,
        } as Workload);
        deleteWorkloadDisclosure.onOpen();
      }
    },
    [deleteModelDisclosure, deleteWorkloadDisclosure],
  );

  const finetuneModelMutation = useMutation({
    mutationFn: async (variables: {
      id: string;
      params: ModelFinetuneParams;
    }) => {
      if (!activeProject) {
        throw new Error('No active project selected');
      }
      return finetuneModel(variables.id, variables.params, activeProject);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['project', activeProject, 'models'],
      });
      toast.success(
        t(
          'customModels.list.actions.finetune.notification.success',
          'Adapter fine-tuning started',
        ),
      );
      finetuneDisclosure.onClose();
    },
    onError: (error) => {
      toast.error(
        t(
          'customModels.list.actions.finetune.notification.error',
          'Error fine-tuning model',
        ),
      );
      console.error('Error fine-tuning model:', error);
    },
  });

  const handleOpenFinetuneModal = useCallback(
    (model?: Model) => {
      setModelToFinetune(model);
      finetuneDisclosure.onOpen();
    },
    [finetuneDisclosure],
  );

  // Count active workloads per model from two sources:
  // - Fine-tuning jobs (PENDING/RUNNING): keyed by workload.id → matches model.id (AIM_MODEL_WORKLOAD_ID_LABEL)
  // - AIM service deployments: keyed by resolvedModel name → matches model.resourceName
  const workloadsCount = useMemo(() => {
    const countMap = new Map<string, number>();
    if (workloads) {
      workloads.forEach((workload) => {
        if (
          workload.type === WorkloadType.FINE_TUNING &&
          (workload.status === WorkloadStatus.PENDING ||
            workload.status === WorkloadStatus.RUNNING)
        ) {
          countMap.set(workload.id, (countMap.get(workload.id) || 0) + 1);
        }
      });
    }
    aimServices.forEach((aim) => {
      const modelName = aim.status.resolvedModel?.name;
      if (modelName) {
        countMap.set(modelName, (countMap.get(modelName) || 0) + 1);
      }
    });
    return countMap;
  }, [workloads, aimServices]);

  // Synthesize in-progress fine-tuning workloads as Model objects so they
  // appear in the table even before an AIMModel CR is created.
  const inProgressFinetuningModels = useMemo<ModelRow[]>(() => {
    if (!workloads || !models) return [];
    const completedResourceNames = new Set(
      models.map((m) => m.resourceName).filter(Boolean),
    );
    return workloads
      .filter(
        (w) =>
          w.type === WorkloadType.FINE_TUNING &&
          w.status !== WorkloadStatus.COMPLETE &&
          !completedResourceNames.has(w.name),
      )
      .map((w) => ({
        name: w.name,
        canonicalName: w.displayName,
        resourceName: w.name,
        source: 'workload' as const,
        status: w.status,
        workloadId: w.id,
      }));
  }, [workloads, models]);

  const filteredModels = useMemo(() => {
    const allModels = [...inProgressFinetuningModels, ...(models ?? [])];
    if (allModels.length === 0) return [];

    const filteredModels = getFilteredData(allModels, filters);
    return filteredModels.reduce<
      (ModelRow & { [ModelsTableField.WORKLOADS]: number })[]
    >((result, model) => {
      const ftCount = model.id ? workloadsCount.get(model.id) || 0 : 0;
      const aimCount = model.resourceName
        ? workloadsCount.get(model.resourceName) || 0
        : 0;
      result.push({
        ...model,
        [ModelsTableField.WORKLOADS]: ftCount + aimCount,
      });

      return result;
    }, []);
  }, [models, inProgressFinetuningModels, filters, workloadsCount]);

  const {
    isOpen: isModelDetailsModalOpen,
    onOpen: onModelDetailsModalOpen,
    onOpenChange: onModelDetailsModalOpenChange,
  } = useDisclosure();

  const [modelBeingSelected, setModelBeingSelected] = useState<
    AIMModelResponse | undefined
  >(undefined);

  const statusFilterItems = useMemo(
    () => [
      {
        key: WorkloadStatus.PENDING,
        label: t('status.pending'),
      },
      {
        key: WorkloadStatus.RUNNING,
        label: t('status.running'),
      },
      {
        key: WorkloadStatus.COMPLETE,
        label: t('status.complete'),
      },
      {
        key: WorkloadStatus.FAILED,
        label: t('status.failed'),
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
      key: ModelsTableField.STATUS,
      sortable: true,
    },
    {
      key: ModelsTableField.WORKLOADS,
      sortable: true,
    },
  ];

  const actions = (item: ModelRow) => {
    const actionsList: ActionItem<ModelRow>[] = [
      {
        key: 'details',
        color: 'default',
        startContent: <IconEye />,
        onPress: (m: ModelRow) => {
          if (m.source === 'workload') {
            router.push({
              pathname: projectPath(`/workloads/${m.workloadId}`),
              query: { ref: router.asPath },
            });
          } else {
            const raw = rawModels?.find(
              (r) => r.metadata.name === m.resourceName,
            );
            setModelBeingSelected(raw);
            onModelDetailsModalOpen();
          }
        },
        label: t('customModels.list.actions.details.label'),
      },
    ];

    if (item.status === WorkloadStatus.COMPLETE) {
      actionsList.push({
        key: 'deploy',
        color: 'default',
        startContent: <IconRocket />,
        onPress: (model: ModelRow) => {
          setModelForAIMDeploy(model);
        },
        label: t('customModels.list.actions.deploy.label'),
      });
    }

    actionsList.push({
      key: 'delete',
      color: 'danger',
      startContent: <IconTrash />,
      onPress: (m: ModelRow) => {
        handleOpenDeleteModal(m);
      },
      label: t('customModels.list.actions.delete.label'),
    });
    return actionsList;
  };

  const customRenderers: Partial<
    Record<ModelsTableField, (item: ModelRow) => React.ReactNode | string>
  > = {
    [ModelsTableField.STATUS]: (item: ModelRow) => (
      <StatusDisplay
        type={item[ModelsTableField.STATUS] as WorkloadStatus}
        variants={getWorkloadStatusVariants(tWorkloads)}
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
            onPress={() => handleOpenFinetuneModal(undefined)}
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
        defaultSortByField={ModelsTableField.NAME}
        defaultSortDirection={SortDirection.ASC}
        customRenderers={
          customRenderers as Record<string, (item: unknown) => React.ReactNode>
        }
        isLoading={isModelsLoading || isWorkloadsLoading}
        isFetching={isModelsRefetching}
        translation={tCustomModels}
        idKey={'resourceName' as never}
        rowActions={actions}
      />

      <ModelDetailsModal
        onOpenChange={onModelDetailsModalOpenChange}
        isOpen={isModelDetailsModalOpen}
        model={modelBeingSelected}
      />

      <DeleteModelModal
        isOpen={deleteModelDisclosure.isOpen}
        onClose={deleteModelDisclosure.onClose}
        model={modelForDeletion}
        hasActiveDeployments={hasActiveDeployments}
        loading={deleteModelMutation.isPending}
        onConfirmAction={({ name }: { name: string }) => {
          deleteModelMutation.mutate({
            name,
            force: hasActiveDeployments,
          });
        }}
      />

      <DeleteWorkloadModal
        isOpen={deleteWorkloadDisclosure.isOpen}
        onOpenChange={deleteWorkloadDisclosure.onOpenChange}
        workload={workloadForDeletion}
        onConfirmAction={(id: string) => {
          deleteWorkloadMutation.mutate(id);
        }}
      />

      {modelForAIMDeploy && activeProject && (
        <DeployFinetuneAIMDrawer
          model={modelForAIMDeploy}
          namespace={activeProject}
          isOpen={true}
          onClose={() => setModelForAIMDeploy(null)}
        />
      )}

      <FinetuneDrawer
        isOpen={finetuneDisclosure.isOpen}
        onOpenChange={finetuneDisclosure.onOpenChange}
        model={modelToFinetune}
        finetunableModels={finetunableModels || []}
        onConfirmAction={({
          id,
          params,
        }: {
          id: string;
          params: ModelFinetuneParams;
        }) => {
          const id_ = modelToFinetune?.id || id;
          finetuneModelMutation.mutate({ id: id_, params });
        }}
      />
    </div>
  );
};

export default CustomModels;
