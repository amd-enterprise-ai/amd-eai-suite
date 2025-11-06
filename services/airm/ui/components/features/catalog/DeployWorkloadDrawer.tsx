// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import {
  Divider,
  Image,
  SelectItem,
  Spinner,
  Switch,
  Tooltip,
} from '@heroui/react';
import { IconInfoCircle } from '@tabler/icons-react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { FieldValues } from 'react-hook-form';

import { useTranslation } from 'next-i18next';

import useSystemToast from '@/hooks/useSystemToast';

import { deployCatalogItem, getCatalogItemById } from '@/services/app/catalog';
import { getCluster } from '@/services/app/clusters';
import { deployModel } from '@/services/app/models';
import { fetchProjectSecrets } from '@/services/app/secrets';
import { getWorkload } from '@/services/app/workloads';

import { bytesToGigabytes } from '@/utils/app/memory';

import { CatalogItem, CatalogItemDeployment } from '@/types/catalog';
import { Cluster } from '@/types/clusters';
import { catalogItemTypeToEndpoint } from '@/types/enums/catalog';
import { WorkloadStatus } from '@/types/enums/workloads';
import { Quota } from '@/types/quotas';
import {
  ProjectSecretWithParentSecret,
  ProjectSecretsResponse,
} from '@/types/secrets';
import { Workload } from '@/types/workloads';

import { DrawerForm } from '@/components/shared/DrawerForm';
import {
  FormInput,
  FormSelect,
  FormSlider,
} from '@/components/shared/ManagedForm';

import DeployingInformer from './DeployingInformer';
import ResourceAllocationInformer from './ResourceAllocationInformer';

import { useProject } from '@/contexts/ProjectContext';
import { formatDate } from 'date-fns';
import { z } from 'zod';

interface Props {
  isOpen: boolean;
  isModelDeployment?: boolean;
  onClose?: () => void;
  onDeployed?: () => void;
  onDeploying?: () => void;
  catalogItem: CatalogItem;
  enableResourceAllocation?: boolean;
}

export const DeployWorkloadDrawer = ({
  enableResourceAllocation = true,
  isModelDeployment = false,
  isOpen,
  onClose,
  onDeployed,
  onDeploying,
  catalogItem,
}: Props) => {
  const { t } = useTranslation('catalog');
  const { toast } = useSystemToast();
  const { activeProject: activeProjectId, projects } = useProject();

  const [isDeploying, setIsDeploying] = useState(false);
  const [isDeployed, setIsDeployed] = useState(false);
  const [workloadId, setWorkloadId] = useState<string>();
  const [customizeResources, setCustomizeResources] = useState<boolean>(false);
  const [prevItem, setPrevItem] = useState<CatalogItem | undefined>(undefined);

  const {
    data: clusterData,
    isLoading: isLoadingClusters,
    isFetching: isFetchingClusters,
    refetch: refetchClusters,
  } = useQuery<Cluster & { quota: Quota }>({
    queryKey: ['cluster'],
    initialData: undefined,
    queryFn: async () => {
      const activeProject = projects.find(
        (project) => project.id === activeProjectId,
      );
      const cluster = await getCluster(activeProject.clusterId);
      return { ...cluster, quota: activeProject.quota };
    },
  });

  const { data: workloadData } = useQuery<Workload>({
    queryKey: ['workload'],
    queryFn: () => getWorkload(workloadId as string),
    refetchInterval: 5000, // Poll every 5 seconds
    enabled: !!workloadId,
  });

  const { data: catalogItemData, isFetching: isFetchingCatalogItem } =
    useQuery<CatalogItem>({
      queryKey: ['catalogItem', catalogItem.id],
      queryFn: () => getCatalogItemById(catalogItem.id),
      enabled: !!catalogItem.id && !isModelDeployment,
    });

  const { data: secretsData, isLoading: isSecretsLoading } =
    useQuery<ProjectSecretsResponse>({
      queryKey: ['secrets', activeProjectId],
      queryFn: () => fetchProjectSecrets(activeProjectId!),
      enabled: !!activeProjectId,
      initialData: { projectSecrets: [] },
      refetchInterval: 10000,
    });

  const { mutate: deployWorkload } = useMutation({
    mutationFn: (payload: CatalogItemDeployment) => {
      return isModelDeployment
        ? deployModel(catalogItem.id, activeProjectId!)
        : deployCatalogItem(payload, activeProjectId!);
    },
    mutationKey: ['deployWorkload'],
    onSuccess: (data) => {
      toast.success(t('notifications.deployWorkload.success'));
      setWorkloadId(data.id);
      if (onDeploying) {
        onDeploying();
      }
    },
    onError: (error) => {
      setIsDeploying(false);
      toast.error(t('notifications.deployWorkload.error'));
      console.error(t('notifications.deployWorkload.error'), error);
    },
  });

  const requiredResources = useMemo(
    () => ({
      gpus: Number(catalogItem?.requiredResources?.gpuCount) || 0,
      memoryPerGpu: Number(catalogItem?.requiredResources?.systemMemory) || 0,
      cpuPerGpu: Number(catalogItem?.requiredResources?.cpuCoreCount) || 0,
    }),
    [catalogItem?.requiredResources],
  );

  const quota = useMemo(
    () => ({
      gpus: clusterData?.quota.gpuCount ?? 0,
      memory: bytesToGigabytes(clusterData?.quota.memoryBytes ?? 0),
      cpu: (clusterData?.quota.cpuMilliCores ?? 0) / 1000,
    }),
    [clusterData],
  );

  const availableResources = useMemo(
    () => ({
      gpus: clusterData?.availableResources.gpuCount ?? 0,
      memory: Math.floor(
        bytesToGigabytes(clusterData?.availableResources.memoryBytes ?? 0),
      ),
      cpu: (clusterData?.availableResources.cpuMilliCores ?? 0) / 1000,
    }),
    [clusterData],
  );

  useEffect(() => {
    if (prevItem !== catalogItem) {
      setPrevItem(catalogItem);
      setWorkloadId(undefined);
      setIsDeploying(false);
      setIsDeployed(false);
      refetchClusters();
    }
  }, [catalogItem, prevItem, refetchClusters]);

  useEffect(() => {
    if (
      isDeploying &&
      !isDeployed &&
      workloadId &&
      workloadData?.status === WorkloadStatus.RUNNING
    ) {
      setIsDeployed(true);
      if (onDeployed) onDeployed();
    }
  }, [isDeploying, isDeployed, workloadId, workloadData?.status, onDeployed]);

  const formSchema = useMemo(
    () =>
      z.object({
        displayName: z
          .string()
          .trim()
          .min(1, {
            message: t('deployModal.settings.displayName.emptyNameError'),
          })
          .max(128),
        containerImage: z
          .string()
          .min(1, {
            message: t('deployModal.settings.containerImage.emptyNameError'),
          })
          .refine(
            (s) =>
              // Check for valid image name format (e.g. registry/repository/image:tag)
              /^(?:[a-z0-9]+(?:[._-][a-z0-9]+)*(?:\/[a-z0-9]+(?:[._-][a-z0-9]+)*)*\/)?[a-z0-9]+(?:[._-][a-z0-9]+)*(?::[\w][\w.-]{0,127})?(?:@sha256:[a-f0-9]{64})?$/.test(
                s,
              ),
            t('deployModal.settings.containerImage.formatError'),
          )
          .optional(),
        imagePullSecrets: z
          .union([z.string(), z.array(z.string())])
          .transform((val) => (typeof val === 'string' ? [val] : val))
          .optional(),
        gpus: z.number().int().optional(),
        memoryPerGpu: z.number().int().optional(),
        cpuPerGpu: z.number().int().optional(),
      }),
    [t],
  );

  const handleDeploy = useCallback(
    (data: FieldValues) => {
      const deploymentPayload = {
        displayName: data.displayName,
        type: catalogItemTypeToEndpoint[catalogItem.type],
        template: catalogItem.slug,
        // Use form values if customizeResources is true, otherwise use requiredResources
        gpus: customizeResources ? data.gpus : requiredResources.gpus,
        memoryPerGpu: customizeResources
          ? data.memoryPerGpu
          : requiredResources.memoryPerGpu,
        cpuPerGpu: customizeResources
          ? data.cpuPerGpu
          : requiredResources.cpuPerGpu,
        image:
          data.containerImage ??
          catalogItemData?.signature?.image ??
          catalogItem.signature?.image ??
          '',
        imagePullSecrets: data.imagePullSecrets,
      };

      setIsDeploying(true);
      deployWorkload(deploymentPayload);
    },
    [
      catalogItem,
      catalogItemData,
      deployWorkload,
      requiredResources,
      customizeResources,
    ],
  );

  const isDeployDisabled = isDeployed || isDeploying || isLoadingClusters;
  const allocationCalculationNotReady =
    isFetchingClusters || isFetchingCatalogItem || !clusterData || !catalogItem;

  return (
    <DrawerForm
      isOpen={isOpen}
      onCancel={onClose}
      onFormSuccess={handleDeploy}
      title={t('deployModal.title')}
      confirmText={t('deployModal.actions.deploy')}
      validationSchema={formSchema}
      cancelText={t('deployModal.actions.cancel')}
      isActioning={isDeploying && !isDeployed}
      isDisabled={isDeployDisabled}
      hideCloseButton={false}
      defaultValues={{
        displayName: `${catalogItem?.slug}-${formatDate(new Date(), 'yyyyMMdd-HHmmss')}`,
      }}
      renderFields={(form) => {
        const {
          gpus = Number(requiredResources.gpus),
          memoryPerGpu = Number(requiredResources.memoryPerGpu),
          cpuPerGpu = Number(requiredResources.cpuPerGpu),
        } = form.watch();

        const currentResources = {
          gpus,
          memoryPerGpu,
          cpuPerGpu,
        };

        return (
          <>
            {!isModelDeployment && !catalogItemData && (
              <div className="flex justify-center items-center h-64">
                <Spinner size="lg" color="primary" />
              </div>
            )}
            {!isDeploying && (isModelDeployment || catalogItemData) && (
              <div className="flex flex-col gap-4 mt-4">
                <div className="flex justify-between items-top">
                  <div>
                    <div className="text-2xl font-bold">
                      {catalogItem?.displayName ?? catalogItem?.name}
                    </div>
                    <div className="text-gray-500">
                      {catalogItem?.description}
                    </div>
                  </div>
                  <Image
                    alt="workload icon"
                    height={40}
                    radius="md"
                    src={catalogItem?.featuredImage || ''}
                    width={40}
                  />
                </div>
                <p className="whitespace-pre-wrap break-words">
                  {catalogItem?.longDescription}
                </p>
                <Divider />
                <div className="text-foreground text-medium uppercase font-bold">
                  {t('deployModal.settings.title')}
                </div>
                <FormInput
                  name="displayName"
                  form={form}
                  aria-label={t('deployModal.settings.displayName.label')}
                  label={t('deployModal.settings.displayName.label')}
                  placeholder={t(
                    'deployModal.settings.displayName.placeholder',
                  )}
                  isRequired
                  maxLength={128}
                />
                {catalogItemData && secretsData && (
                  <>
                    <FormInput
                      name="containerImage"
                      form={form}
                      aria-label={t(
                        'deployModal.settings.containerImage.label',
                      )}
                      label={
                        <div className="flex items-center gap-1">
                          <span>
                            {t('deployModal.settings.containerImage.label')}
                          </span>
                          <Tooltip
                            classNames={{
                              content: 'max-w-md',
                            }}
                            content={t(
                              'deployModal.settings.containerImage.tooltip',
                            )}
                          >
                            <IconInfoCircle
                              className="text-default-400 cursor-pointer"
                              size={16}
                            />
                          </Tooltip>
                        </div>
                      }
                      defaultValue={catalogItemData?.signature?.image}
                    />
                    <FormSelect
                      name="imagePullSecrets"
                      form={form}
                      aria-label={t(
                        'deployModal.settings.imagePullSecrets.label',
                      )}
                      selectionMode="multiple"
                      label={
                        <div className="flex items-center gap-1">
                          <span>
                            {t('deployModal.settings.imagePullSecrets.label')}
                          </span>
                          <Tooltip
                            classNames={{
                              content: 'max-w-md',
                            }}
                            content={t(
                              'deployModal.settings.imagePullSecrets.tooltip',
                            )}
                          >
                            <IconInfoCircle
                              className="text-default-400 cursor-pointer"
                              size={16}
                            />
                          </Tooltip>
                        </div>
                      }
                      placeholder={
                        secretsData.projectSecrets.length === 0
                          ? t('deployModal.settings.imagePullSecrets.noSecrets')
                          : t(
                              'deployModal.settings.imagePullSecrets.placeholder',
                            )
                      }
                      isLoading={isSecretsLoading}
                      disabled={secretsData.projectSecrets.length === 0}
                    >
                      {secretsData.projectSecrets.map(
                        (secret: ProjectSecretWithParentSecret) => (
                          <SelectItem key={secret.secret.name}>
                            {secret.secret.name}
                          </SelectItem>
                        ),
                      )}
                    </FormSelect>
                  </>
                )}
                {!isModelDeployment && (
                  <Switch
                    isSelected={customizeResources}
                    onChange={(e) => {
                      setCustomizeResources(e.target.checked);
                    }}
                    size="md"
                    className="max-w-md"
                    isDisabled={isLoadingClusters || !enableResourceAllocation}
                  >
                    {t('deployModal.settings.resourceAllocation.label')}
                  </Switch>
                )}

                {customizeResources && (
                  <div>
                    <FormSlider
                      form={form}
                      name="gpus"
                      defaultValue={requiredResources.gpus}
                      key={`gpus-slider-${requiredResources.gpus}`}
                      label={t(
                        'deployModal.settings.resourceAllocation.gpuCount',
                      )}
                      isDisabled={allocationCalculationNotReady}
                      maxValue={availableResources.gpus}
                      minValue={0}
                      step={1}
                      getValue={(value) =>
                        `${t(
                          'deployModal.settings.resourceAllocation.gpuCountValue',
                          {
                            value,
                            maxValue: availableResources.gpus,
                          },
                        )}`
                      }
                      marks={[
                        {
                          value: requiredResources.gpus as number,
                          label: t(
                            'deployModal.settings.resourceAllocation.req',
                          ),
                        },
                      ]}
                    />

                    <FormSlider
                      form={form}
                      name="memoryPerGpu"
                      defaultValue={requiredResources.memoryPerGpu}
                      key={`memoryPerGpu-slider-${requiredResources.memoryPerGpu}`}
                      label={t(
                        'deployModal.settings.resourceAllocation.systemMemory',
                      )}
                      isDisabled={allocationCalculationNotReady}
                      maxValue={Math.ceil(
                        availableResources.memory / Math.max(gpus, 1),
                      )}
                      minValue={1}
                      step={1}
                      getValue={(item) =>
                        `${t(
                          'deployModal.settings.resourceAllocation.systemMemoryValue',
                          {
                            value: item,
                            maxValue: Math.ceil(
                              availableResources.memory /
                                Math.max(currentResources.gpus, 1),
                            ),
                          },
                        )}`
                      }
                      marks={[
                        {
                          value: requiredResources.memoryPerGpu as number,
                          label: t(
                            'deployModal.settings.resourceAllocation.req',
                          ),
                        },
                      ]}
                    />

                    <FormSlider
                      form={form}
                      name="cpuPerGpu"
                      defaultValue={requiredResources.cpuPerGpu}
                      key={`cpuPerGpu-slider-${requiredResources.cpuPerGpu}`}
                      label={t(
                        'deployModal.settings.resourceAllocation.cpuCoreCount',
                      )}
                      isDisabled={allocationCalculationNotReady}
                      maxValue={Math.ceil(
                        availableResources.cpu /
                          Math.max(currentResources.gpus, 1),
                      )}
                      minValue={1}
                      step={1}
                      getValue={(item) =>
                        `${t(
                          'deployModal.settings.resourceAllocation.cpuCoreCountValue',
                          {
                            value: item,
                            maxValue: Math.ceil(
                              availableResources.cpu /
                                Math.max(currentResources.gpus, 1),
                            ),
                          },
                        )}`
                      }
                      marks={[
                        {
                          value: requiredResources.cpuPerGpu as number,
                          label: t(
                            'deployModal.settings.resourceAllocation.req',
                          ),
                        },
                      ]}
                    />
                  </div>
                )}

                {!isModelDeployment && (
                  <>
                    <Divider />
                    <ResourceAllocationInformer
                      isLoading={isLoadingClusters}
                      currentResources={
                        customizeResources
                          ? {
                              gpus,
                              memoryPerGpu,
                              cpuPerGpu,
                            }
                          : requiredResources
                      }
                      quota={quota}
                      requiredResources={requiredResources}
                    />
                  </>
                )}
              </div>
            )}
            {isDeploying && (
              <DeployingInformer
                name={catalogItem?.name}
                isDeployed={isDeployed}
                isModelDeployment={isModelDeployment}
                workloadData={workloadData}
                workloadId={workloadId || ''}
                t={t}
              />
            )}
          </>
        );
      }}
    />
  );
};

DeployWorkloadDrawer.displayName = 'DeployWorkloadDrawer';
