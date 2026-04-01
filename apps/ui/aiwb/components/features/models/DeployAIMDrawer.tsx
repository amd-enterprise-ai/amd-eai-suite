// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import { Divider, Selection, SelectItem, Switch, Tooltip } from '@heroui/react';
import { IconAlertTriangle, IconInfoCircle } from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Controller } from 'react-hook-form';
import type { UseFormReturn } from 'react-hook-form';
import { z } from 'zod';

import { AutoscalingFormFields } from '@/components/features/models/AutoscalingFormFields';
import { DEFAULT_AUTOSCALING } from '@/lib/app/aims';

import { useTranslation } from 'next-i18next';

import { Alert } from '@amdenterpriseai/components';
import { useSystemToast } from '@amdenterpriseai/hooks';

import { validateHuggingFaceTokenFields } from '@/lib/app/huggingface-secret';

import { SecretUseCase } from '@amdenterpriseai/types';

import {
  createAimScalingPolicyConfig,
  deployAim,
  getAimServiceTemplates,
} from '@/lib/app/aims';
import {
  AIMClusterServiceTemplate,
  AIMDeployPayload,
  AIMStatus,
  ParsedAIM,
  AggregatedAIM,
} from '@/types/aims';
import { SecretResponseData } from '@/types/secrets';
import { fetchProjectSecrets, createProjectSecret } from '@/lib/app/secrets';

import { HuggingFaceTokenSelector } from '@amdenterpriseai/components';

import { ModelIcon } from '@/components/shared/ModelIcons';
import { DrawerForm } from '@amdenterpriseai/components';
import { FormSelect } from '@amdenterpriseai/components';

import { useProject } from '@/contexts/ProjectContext';
import type { APIRequestError } from '@amdenterpriseai/utils/app';

import { UnoptimizedProfileBadge } from './UnoptimizedProfileBadge';

function getReadyTemplatesFrom(
  templates: AIMClusterServiceTemplate[],
): AIMClusterServiceTemplate[] {
  return (templates ?? []).filter((t) => t.status?.status === 'Ready');
}

function getMetricsStatusMap(
  readyTemplates: AIMClusterServiceTemplate[],
): Record<string, boolean> {
  const result: Record<string, boolean> = {};
  for (const template of readyTemplates) {
    const metric = template.spec?.metric;
    if (metric === undefined) continue;
    const isOptimized =
      template.status?.profile?.metadata?.type === 'optimized';
    result[metric] = result[metric] || isOptimized;
  }
  return result;
}

interface DeployAIMFormValues {
  model: string;
  selectedToken?: string;
  tokenName?: string;
  token?: string;
  metric?: string;
  autoscalingEnabled: boolean;
  minReplicas?: number;
  maxReplicas?: number;
  metricQuery?: string;
  operationOverTime?: string;
  targetType?: string;
  targetValue?: number;
}

interface Props {
  isOpen: boolean;
  onClose?: () => void;
  onDeployed?: () => void;
  onDeploying?: () => void;
  aggregatedAim: AggregatedAIM;
}

export const DeployAIMDrawer = ({
  isOpen,
  onClose,
  onDeploying,
  aggregatedAim,
}: Props) => {
  const { t } = useTranslation('models');
  const { toast } = useSystemToast();
  const { activeProject: namespace } = useProject();
  const queryClient = useQueryClient();

  const defaultAim = useMemo(
    () =>
      aggregatedAim.latestAim ??
      aggregatedAim.parsedAIMs.find((a) => a.status === AIMStatus.READY) ??
      aggregatedAim.parsedAIMs[0]!,
    [aggregatedAim],
  );

  const [isDeploying, setIsDeploying] = useState(false);
  const [selectedAim, setSelectedAim] = useState<ParsedAIM>(() => defaultAim);

  const formRef = useRef<UseFormReturn<DeployAIMFormValues> | null>(null);

  // Update selectedAim when aggregatedAim changes
  useEffect(() => {
    setSelectedAim(defaultAim);
  }, [defaultAim]);

  const handleModelChange = (keys: Selection) => {
    if (keys === 'all') return;
    const selected = Array.from(keys)[0] as string;
    const match = aggregatedAim.parsedAIMs.find(
      (aim) => aim.resourceName === selected,
    );
    if (match) {
      setSelectedAim(match);
    }
  };

  if (!namespace) {
    return null;
  }

  const { data: projectSecrets } = useQuery<SecretResponseData[]>({
    queryKey: ['project', namespace, 'secrets'],
    queryFn: async () => {
      const response = await fetchProjectSecrets(namespace);
      return response.data;
    },
    enabled: isOpen && selectedAim.isHfTokenRequired,
  });

  // Fetch service templates for the AIM to get optimization metrics
  const { data: serviceTemplates, isLoading: templatesLoading } = useQuery<
    AIMClusterServiceTemplate[]
  >({
    queryKey: ['aim-templates', selectedAim.resourceName],
    queryFn: () => getAimServiceTemplates(selectedAim.resourceName),
    enabled: isOpen && !!selectedAim.resourceName,
  });

  const readyTemplates = getReadyTemplatesFrom(serviceTemplates ?? []);
  const metricsStatusMap = getMetricsStatusMap(readyTemplates);
  const metricsWithStatus = Object.entries(metricsStatusMap).map(
    ([metric, isOptimized]) => ({ metric, isOptimized }),
  );
  const isAtleastOneOptimized =
    Object.keys(metricsStatusMap).length === 0 ||
    Object.values(metricsStatusMap).some((v) => v);

  const huggingFaceTokens =
    projectSecrets?.filter((ps) => ps.useCase === SecretUseCase.HUGGING_FACE) ??
    [];

  const createSecretMutation = useMutation({
    mutationFn: (secretRequest: Parameters<typeof createProjectSecret>[1]) =>
      createProjectSecret(namespace, secretRequest),
    onSuccess: (createdSecret: SecretResponseData, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['project', namespace, 'secrets'],
      });

      toast.success(
        t('huggingFaceTokenDrawer.notifications.secretCreated', {
          name: variables.name,
        }),
      );
    },
    onError: (error: Error) => {
      toast.error(
        t('huggingFaceTokenDrawer.notifications.secretCreateError', {
          error: error.message,
        }),
      );
    },
  });

  const formSchema = useMemo(
    () =>
      z
        .object({
          model: z.string().min(1, 'Version is required'),
          selectedToken: z.string().optional(),
          tokenName: z.string().optional(),
          token: z.string().optional(),
          metric: z.string().optional(),
          autoscalingEnabled: z.boolean(),
          minReplicas: z.number().min(1).max(30).optional(),
          maxReplicas: z.number().min(1).max(30).optional(),
          metricQuery: z.string().optional(),
          operationOverTime: z.string().optional(),
          targetType: z.string().optional(),
          targetValue: z.number().min(1).optional(),
        })
        // Hugging Face token validation
        .superRefine((data, ctx) => {
          // Skip validation if Hugging Face token is not required
          if (!selectedAim.isHfTokenRequired) return;

          // If user selected an existing token, validation passes, otherwise validate HF token
          if (data.selectedToken) return;
          validateHuggingFaceTokenFields(data, ctx, t);
        })
        // Autoscaling validation
        .superRefine((data, ctx) => {
          if (
            data.autoscalingEnabled &&
            data.minReplicas &&
            data.maxReplicas &&
            data.minReplicas > data.maxReplicas
          ) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message:
                'Min replicas must be less than or equal to max replicas',
              path: ['maxReplicas'],
            });
          }
        }),
    [t, selectedAim.isHfTokenRequired],
  );

  const handleDeploy = useCallback(
    async (data: DeployAIMFormValues) => {
      const buildAndSubmitDeploy = async (hfTokenName?: string) => {
        try {
          setIsDeploying(true);

          const payload: AIMDeployPayload = {
            model: data.model,
            replicas: 1,
            allowUnoptimized: true,
          };

          if (hfTokenName) payload.hfToken = hfTokenName;
          if (data.metric) payload.metric = data.metric;

          // Add autoscaling configuration if enabled
          if (data.autoscalingEnabled) {
            const {
              minReplicas,
              maxReplicas,
              metricQuery,
              operationOverTime,
              targetType,
              targetValue,
            } = data;

            payload.minReplicas = minReplicas;
            payload.maxReplicas = maxReplicas;

            payload.autoScaling = createAimScalingPolicyConfig({
              metricQuery,
              operationOverTime,
              targetType,
              targetValue,
            });
          }

          await deployAim(namespace, payload);
          if (onClose) onClose();
          toast.success(t('deployAIMDrawer.notifications.success'));
          if (onDeploying) onDeploying();
        } catch (error) {
          toast.error(
            t('deployAIMDrawer.notifications.error', {
              message: (error as APIRequestError).message || 'Unknown error',
            }),
            error as APIRequestError,
          );
        } finally {
          setIsDeploying(false);
        }
      };

      // No token provided or not required - deploy without hfToken
      if (!selectedAim.isHfTokenRequired) {
        buildAndSubmitDeploy();
        return;
      }

      const { selectedToken, tokenName, token } = data;

      // If a token is selected from dropdown
      if (selectedToken) {
        // selectedToken is the index from the SelectItem
        const tokenIndex = parseInt(selectedToken, 10);
        const selectedTokenHf = huggingFaceTokens[tokenIndex];

        if (!selectedTokenHf) {
          toast.error(
            t('huggingFaceTokenDrawer.notifications.noTokenSelected'),
          );
          return;
        }

        buildAndSubmitDeploy(selectedTokenHf.metadata.name);
        return;
      }

      const isNewToken = tokenName && token;

      if (isNewToken) {
        const secretRequest = {
          name: tokenName,
          data: {
            token: Buffer.from(token, 'utf-8').toString('base64'),
          },
          use_case: SecretUseCase.HUGGING_FACE,
        };

        const createdSecret = await createSecretMutation.mutateAsync(
          secretRequest as any,
        );

        if (!createdSecret || !createdSecret.metadata?.name) {
          toast.error(
            t('huggingFaceTokenDrawer.notifications.invalidSecretResponse'),
          );
          setIsDeploying(false);
          return;
        }

        buildAndSubmitDeploy(createdSecret.metadata.name);

        return;
      }

      if (!namespace) {
        toast.error(t('deployAIMDrawer.notifications.noTokenSelected'));
        return;
      }
    },
    [
      namespace,
      selectedAim.resourceName,
      selectedAim.isHfTokenRequired,
      onClose,
      onDeploying,
      t,
      toast,
      createSecretMutation,
      huggingFaceTokens,
    ],
  );

  const isDeployDisabled = isDeploying || templatesLoading;

  return (
    <DrawerForm<DeployAIMFormValues>
      isOpen={isOpen}
      onCancel={onClose}
      onFormSuccess={handleDeploy}
      onFormFailure={(errors) => {
        console.error('Form validation failed:', errors);
      }}
      title={t('deployAIMDrawer.title')}
      confirmText={t('deployAIMDrawer.actions.deploy')}
      validationSchema={formSchema}
      cancelText={t('deployAIMDrawer.actions.cancel')}
      isActioning={isDeploying}
      isDisabled={isDeployDisabled}
      hideCloseButton={false}
      defaultValues={{
        model: defaultAim.resourceName,
        selectedToken: '',
        tokenName: '',
        token: '',
        metric: '',
        autoscalingEnabled: false,
        ...DEFAULT_AUTOSCALING,
      }}
      renderFields={(form) => {
        formRef.current = form;
        const selectedMetric = form.watch('metric');
        // If no metric selected, AIMService will pick the best, otherwise check it from map.
        const selectedMetricOptimized =
          !selectedMetric ||
          (selectedMetric != null &&
            selectedMetric !== '' &&
            metricsStatusMap[selectedMetric] === true);
        const showWarning = !isAtleastOneOptimized || !selectedMetricOptimized;

        return (
          <div className="flex flex-col gap-4 mt-4">
            <div className="flex justify-between items-top">
              <div>
                <div className="text-2xl font-bold">{selectedAim?.title}</div>
                <p>{selectedAim?.description.short}</p>
              </div>

              <div className="w-12 h-12">
                <ModelIcon
                  iconName={selectedAim.canonicalName}
                  width={48}
                  height={48}
                />
              </div>
            </div>
            <p className="whitespace-pre-wrap wrap-break-words">
              {selectedAim?.description.full}
            </p>
            <Divider />
            <div className="text-foreground text-medium uppercase font-bold">
              {t('deployAIMDrawer.fields.title')}
            </div>
            <FormSelect
              label={t('deployAIMDrawer.fields.version.title')}
              name="model"
              form={form}
              aria-label={t('deployAIMDrawer.fields.version.label')}
              placeholder={t('deployAIMDrawer.fields.version.placeholder')}
              onSelectionChange={handleModelChange}
              disabledKeys={aggregatedAim.parsedAIMs
                .filter((v) => v.status !== AIMStatus.READY)
                .map((v) => v.resourceName)}
            >
              {aggregatedAim.parsedAIMs.map((version) => {
                const isUnsupported = version.status !== AIMStatus.READY;
                const labels = [version.imageVersion];
                if (version.isLatest) {
                  labels.push(
                    `(${t('deployAIMDrawer.fields.version.latest')})`,
                  );
                }
                if (isUnsupported) {
                  labels.push(
                    `(${t('deployAIMDrawer.fields.version.unsupported')})`,
                  );
                }
                return (
                  <SelectItem key={version.resourceName}>
                    {labels.join(' ')}
                  </SelectItem>
                );
              })}
            </FormSelect>
            {selectedAim.isHfTokenRequired && (
              <>
                <div className="flex items-center gap-1">
                  <h3 className="text-medium font-medium text-foreground">
                    {t('deployAIMDrawer.fields.huggingFaceToken.title')}
                  </h3>
                  <Tooltip
                    classNames={{
                      content: 'max-w-md',
                    }}
                    content={t(
                      'deployAIMDrawer.fields.huggingFaceToken.description',
                    )}
                  >
                    <IconInfoCircle
                      className="text-default-400 cursor-pointer"
                      size={16}
                    />
                  </Tooltip>
                </div>
                <HuggingFaceTokenSelector
                  form={form}
                  existingTokens={huggingFaceTokens}
                  fieldNames={{
                    selectedToken: 'selectedToken',
                    name: 'tokenName',
                    token: 'token',
                  }}
                />
              </>
            )}
            {metricsWithStatus.length > 0 && (
              <>
                <div className="flex items-center gap-1">
                  <h3 className="text-medium font-medium text-foreground">
                    {t('deployAIMDrawer.fields.metric.title')}
                  </h3>
                  <Tooltip
                    classNames={{
                      content: 'max-w-md whitespace-pre-line',
                    }}
                    content={t('deployAIMDrawer.fields.metric.description')}
                  >
                    <IconInfoCircle
                      className="text-default-400 cursor-pointer"
                      size={16}
                    />
                  </Tooltip>
                </div>
                <FormSelect
                  name="metric"
                  form={form}
                  aria-label={t('deployAIMDrawer.fields.metric.label')}
                  placeholder={t('deployAIMDrawer.fields.metric.placeholder')}
                  classNames={{
                    value: 'capitalize',
                    trigger: 'min-w-[16rem] w-full',
                  }}
                  endContent={
                    showWarning ? (
                      <UnoptimizedProfileBadge
                        label={t(
                          'deployAIMDrawer.fields.metric.unoptimizedLabel',
                        )}
                      />
                    ) : null
                  }
                >
                  {metricsWithStatus.map(({ metric, isOptimized }) => (
                    <SelectItem
                      key={metric}
                      className="capitalize"
                      textValue={metric}
                      endContent={
                        !isOptimized ? (
                          <UnoptimizedProfileBadge
                            label={t(
                              'deployAIMDrawer.fields.metric.unoptimizedLabel',
                            )}
                          />
                        ) : undefined
                      }
                    >
                      {t(`performanceMetrics.values.${metric}`)}
                    </SelectItem>
                  ))}
                </FormSelect>
              </>
            )}

            {/* ====== AUTOSCALING SECTION ====== */}
            <Divider />
            <div className="flex flex-col gap-4">
              {/* Autoscaling Header */}
              <div className="flex items-center gap-1">
                <h3 className="text-medium font-medium text-foreground">
                  {t('deployAIMDrawer.fields.autoscaling.title')}
                </h3>
              </div>

              {/* Autoscaling Toggle */}
              <Controller
                name="autoscalingEnabled"
                control={form.control}
                render={({ field }) => (
                  <div className="flex flex-col gap-0">
                    <Switch
                      data-testid="autoscaling-toggle"
                      isSelected={field.value}
                      onValueChange={field.onChange}
                    >
                      {t('deployAIMDrawer.fields.autoscaling.enable')}
                    </Switch>
                    <p
                      role="note"
                      className="text-small text-default-500 ml-[58px]"
                    >
                      {t('helper', { ns: 'autoscaling' })}
                    </p>
                  </div>
                )}
              />

              {/* Autoscaling Configuration - Only shown when enabled */}
              {form.watch('autoscalingEnabled') && (
                <AutoscalingFormFields
                  form={form}
                  className="flex flex-col gap-4 pl-1"
                />
              )}
            </div>

            <Divider />

            {showWarning && (
              <Alert
                color="warning"
                variant="bordered"
                title={t('deployAIMDrawer.fields.metric.unoptimizedLabel')}
                description={t('deployAIMDrawer.fields.metric.notOptimized')}
                classNames={{
                  title: 'text-foreground',
                  description: 'text-default-600',
                }}
              />
            )}
          </div>
        );
      }}
    />
  );
};

DeployAIMDrawer.displayName = 'DeployAIMDrawer';
