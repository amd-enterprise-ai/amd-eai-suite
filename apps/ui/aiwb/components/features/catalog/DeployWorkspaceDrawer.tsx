// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import {
  SelectItem,
  Divider,
  DrawerForm,
  FormInput,
  FormSelect,
  FormSlider,
  LinkToast,
  Switch,
  Tooltip,
} from '@amdenterpriseai/components';

import { PageLoader } from '@/components/shared/PageLoader';
import { IconInfoCircle } from '@tabler/icons-react';
import { useMutation, useQuery } from '@tanstack/react-query';
import Image from 'next/image';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { FieldValues } from 'react-hook-form';

import { useTranslation } from 'next-i18next';

import { useSystemToast } from '@amdenterpriseai/hooks';

import { bytesToGigabytes } from '@amdenterpriseai/utils/app';

import { CatalogItem } from '@/types/catalog';
import { CatalogItemDeployment } from '@/types/catalog';
import { catalogItemTypeToEndpoint } from '@/types/enums/catalog';
import { SecretUseCase } from '@amdenterpriseai/types';
import { WorkloadStatus } from '@/types/enums/workloads';
import { Workload } from '@/types/workloads';

import DeployingInformer from './DeployingInformer';
import ResourceAllocationInformer from './ResourceAllocationInformer';

import { useProject } from '@/contexts/ProjectContext';
import { z } from 'zod';
import { getClusterResources } from '@/lib/app/cluster';
import { ClusterResources } from '@/types/cluster';
import { fetchProjectSecrets } from '@/lib/app/secrets';
import { SecretResponseData } from '@/types/secrets';
import {
  deployWorkspace,
  getCatalogItemById,
  getWorkload,
} from '@/lib/app/workloads';

interface Props {
  isOpen: boolean;
  onClose?: () => void;
  onDeployed?: () => void;
  onDeploying?: () => void;
  catalogItem: CatalogItem;
  enableResourceAllocation?: boolean;
}

export const DeployWorkspaceDrawer = ({
  enableResourceAllocation = true,
  isOpen,
  onClose,
  onDeployed,
  onDeploying,
  catalogItem,
}: Props) => {
  const { t } = useTranslation('catalog');
  const { toast } = useSystemToast();
  const { activeProject: activeProjectId, projects, projectUrl } = useProject();

  const [isDeploying, setIsDeploying] = useState(false);
  const [isDeployed, setIsDeployed] = useState(false);
  const [workloadId, setWorkloadId] = useState<string>();
  const [customizeResources, setCustomizeResources] = useState<boolean>(false);
  const [prevItem, setPrevItem] = useState<CatalogItem | undefined>(undefined);

  const {
    data: clusterResourcesData,
    isLoading: isLoadingClusterResources,
    isFetching: isFetchingClusterResources,
    refetch: refetchClusterResources,
  } = useQuery<ClusterResources>({
    queryKey: ['cluster', 'resources'],
    initialData: undefined,
    queryFn: async () => {
      const clusterResources = await getClusterResources();
      return { ...clusterResources.data };
    },
  });

  const { data: workloadData } = useQuery<Workload>({
    queryKey: ['workload'],
    queryFn: () => getWorkload(workloadId as string, activeProjectId!),
    refetchInterval: 5000, // Poll every 5 seconds
    enabled: !!workloadId && !!activeProjectId,
  });

  const { data: catalogItemData, isFetching: isFetchingCatalogItem } =
    useQuery<CatalogItem>({
      queryKey: ['catalogItem', catalogItem.id],
      queryFn: () => getCatalogItemById(catalogItem.id),
      enabled: !!catalogItem.id,
    });

  const { data: secretsData, isLoading: isSecretsLoading } = useQuery<{
    data: SecretResponseData[];
  }>({
    queryKey: ['secrets', activeProjectId, SecretUseCase.IMAGE_PULL_SECRET],
    queryFn: () =>
      fetchProjectSecrets(activeProjectId!, SecretUseCase.IMAGE_PULL_SECRET),
    enabled: !!activeProjectId,
    initialData: { data: [] },
    refetchInterval: 10000,
  });

  const { mutate: deployWorkload } = useMutation({
    mutationFn: (payload: CatalogItemDeployment) => {
      return deployWorkspace(activeProjectId!, payload);
    },
    mutationKey: ['deployWorkload'],
    onSuccess: async (data) => {
      const workloadId = data.id;

      toast.success(
        <LinkToast
          message={t('notifications.deployWorkload.success')}
          href={projectUrl(`/workloads/${workloadId}`)}
        />,
      );
      setWorkloadId(workloadId);
      if (onDeploying) {
        onDeploying();
      }
      onClose?.();
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

  const availableResources = useMemo(
    () => ({
      gpus: clusterResourcesData?.availableResources.gpuCount ?? 0,
      memory: Math.floor(
        bytesToGigabytes(
          clusterResourcesData?.availableResources.memoryBytes ?? 0,
        ),
      ),
      cpu: (clusterResourcesData?.availableResources.cpuMilliCores ?? 0) / 1000,
    }),
    [clusterResourcesData],
  );

  useEffect(() => {
    if (prevItem !== catalogItem) {
      setPrevItem(catalogItem);
      setWorkloadId(undefined);
      setIsDeploying(false);
      setIsDeployed(false);
      refetchClusterResources();
    }
  }, [catalogItem, prevItem, refetchClusterResources]);

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

  const isDeployDisabled =
    isDeployed || isDeploying || isLoadingClusterResources;
  const allocationCalculationNotReady =
    isFetchingClusterResources ||
    isFetchingCatalogItem ||
    !clusterResourcesData ||
    !catalogItem;

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
        displayName: catalogItem?.displayName ?? catalogItem?.name ?? '',
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
            {!catalogItemData && (
              <PageLoader
                label={t('deployModal.loading')}
                testId="deploy-drawer-loading"
                className="h-64"
              />
            )}
            {!isDeploying && catalogItemData && (
              <div className="flex flex-col gap-4 mt-4">
                <div className="flex justify-between items-top">
                  <div>
                    <div className="text-2xl font-bold">
                      {catalogItem?.displayName ?? catalogItem?.name}
                    </div>
                    <p>{catalogItem?.description}</p>
                  </div>
                  {catalogItem?.featuredImage && (
                    <Image
                      alt="workload icon"
                      className="h-10 w-10 shrink-0 self-start rounded-md object-cover"
                      height={40}
                      src={catalogItem.featuredImage}
                      width={40}
                      unoptimized
                    />
                  )}
                </div>
                {/* TODO: Introduce the MD renderer here instead of using a raw string. */}
                <p className="whitespace-pre-wrap wrap-break-words flex flex-col gap-4">
                  {catalogItem?.longDescription?.replace(/\\n/g, '\n')}
                </p>
                <Divider />
                <div className="text-foreground text-base uppercase font-bold">
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
                        secretsData.data.length === 0
                          ? t('deployModal.settings.imagePullSecrets.noSecrets')
                          : t(
                              'deployModal.settings.imagePullSecrets.placeholder',
                            )
                      }
                      isLoading={isSecretsLoading}
                      disabled={secretsData.data.length === 0}
                    >
                      {secretsData.data.map((secret: SecretResponseData) => (
                        <SelectItem key={secret.metadata.name}>
                          {secret.metadata.name}
                        </SelectItem>
                      ))}
                    </FormSelect>
                  </>
                )}
                <Switch
                  isSelected={customizeResources}
                  onChange={(e) => {
                    setCustomizeResources(e.target.checked);
                  }}
                  size="md"
                  className="max-w-md"
                  isDisabled={
                    isLoadingClusterResources || !enableResourceAllocation
                  }
                >
                  {t('deployModal.settings.resourceAllocation.label')}
                </Switch>

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

                <Divider />
                <ResourceAllocationInformer
                  isLoading={isLoadingClusterResources}
                  currentResources={
                    customizeResources
                      ? {
                          gpus,
                          memoryPerGpu,
                          cpuPerGpu,
                        }
                      : requiredResources
                  }
                  quota={undefined}
                  requiredResources={requiredResources}
                />
              </div>
            )}
            {isDeploying && (
              <DeployingInformer
                name={catalogItem?.name}
                isDeployed={isDeployed}
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

DeployWorkspaceDrawer.displayName = 'DeployWorkspaceDrawer';
