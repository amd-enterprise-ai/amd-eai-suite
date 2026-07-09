// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT
import {
  Selection,
  SelectItem,
  Divider,
  Alert,
  DrawerForm,
  FormInput,
  FormSelect,
  FormSwitch,
  Tooltip,
} from '@amdenterpriseai/components';
import { IconEye, IconEyeOff, IconInfoCircle } from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { UseFormReturn } from 'react-hook-form';
import { z } from 'zod';

import { AutoscalingFormFields } from '@/components/features/models/AutoscalingFormFields';
import { DEFAULT_AUTOSCALING } from '@/lib/app/aims';

import { useTranslation } from 'next-i18next';

import { useSystemToast } from '@amdenterpriseai/hooks';

import {
  createHuggingFaceSecretRequest,
  validateHuggingFaceTokenFields,
} from '@/lib/app/huggingface-secret';

import { SecretUseCase } from '@amdenterpriseai/types';

import {
  createAimScalingPolicyConfig,
  getAimClusterProfiles,
  getMetricTranslationKey,
} from '@/lib/app/aims';
import { deployInference } from '@/lib/app/inference';
import {
  ADVANCED_PARAM_AUTOMATIC,
  filterProfilesByAdvancedParams,
} from '@/lib/app/aims/filterProfilesByAdvancedParams';
import {
  AIM_PROFILE_TYPE_OPTIMIZED,
  AIMClusterProfile,
  AIMDeployPayload,
  AIMStatus,
  AggregatedAIM,
  ParsedAIM,
} from '@/types/aims';
import { SecretResponseData } from '@/types/secrets';
import { fetchProjectSecrets, createProjectSecret } from '@/lib/app/secrets';

import { ModelIcon } from '@/components/shared/ModelIcons';

import { useProject } from '@/contexts/ProjectContext';
import { APIRequestError } from '@amdenterpriseai/utils/app';

import {
  DeployAIMAdvancedProfileFields,
  type DeployAIMFormValues,
} from './DeployAIMAdvancedProfileFields';
import { UnoptimizedProfileBadge } from './UnoptimizedProfileBadge';
import { HuggingFaceTokenSelector } from '@/components/shared/HuggingFaceTokenSelector';

function getReadyProfilesFrom(
  profiles: AIMClusterProfile[],
): AIMClusterProfile[] {
  return (profiles ?? []).filter((p) => p.status?.status === 'Ready');
}

function getMetricsStatusMap(
  readyProfiles: AIMClusterProfile[],
): Record<string, boolean> {
  const result: Record<string, boolean> = {};
  for (const profile of readyProfiles) {
    const metric = profile.spec?.metric;
    if (metric === undefined || metric === null) continue;
    const metricKey = String(metric);
    const isOptimized = profile.spec?.type === AIM_PROFILE_TYPE_OPTIMIZED;
    result[metricKey] = result[metricKey] || isOptimized;
  }
  return result;
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
  const [showAdvancedProfileParams, setShowAdvancedProfileParams] =
    useState(false);

  const formRef = useRef<UseFormReturn<DeployAIMFormValues> | null>(null);

  // Update selectedAim when aggregatedAim changes
  useEffect(() => {
    setSelectedAim(defaultAim);
  }, [defaultAim]);

  useEffect(() => {
    if (!isOpen) {
      setShowAdvancedProfileParams(false);
    }
  }, [isOpen]);

  const handleModelChange = (keys: Selection) => {
    if (keys === 'all') return;
    const selected = Array.from(keys)[0] as string;
    const match = aggregatedAim.parsedAIMs.find(
      (aim) => aim.model === selected,
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
    enabled: isOpen,
  });

  // Fetch profiles for the AIM to get optimization metrics
  const {
    data: serviceProfiles,
    isLoading: profilesLoading,
    isError: profilesError,
    error: profilesErrorObj,
  } = useQuery<AIMClusterProfile[]>({
    queryKey: ['aim-profiles', selectedAim.aimId],
    queryFn: () => getAimClusterProfiles(selectedAim.aimId ?? ''),
    enabled: isOpen && !!selectedAim.aimId,
    retry: (failureCount, error) => {
      // The profiles endpoint returns 200 + empty data when no profiles match,
      // so a 404 here means the proxy/route is misconfigured (or upstream is
      // unreachable) — retrying won't recover. Other failures (network blips,
      // 5xx) get the standard 3 retries.
      if (error instanceof APIRequestError && error.statusCode === 404) {
        return false;
      }
      return failureCount < 3;
    },
  });

  const readyProfiles = useMemo(
    () => getReadyProfilesFrom(serviceProfiles ?? []),
    [serviceProfiles],
  );
  const metricsStatusMap = getMetricsStatusMap(readyProfiles);
  const metricsWithStatus = Object.entries(metricsStatusMap).map(
    ([metric, isOptimized]) => ({ metric, isOptimized }),
  );
  const isAtleastOneOptimized =
    Object.keys(metricsStatusMap).length === 0 ||
    Object.values(metricsStatusMap).some((v) => v);

  const advancedProfileOptions = useMemo(() => {
    const optimizationClasses = new Set<string>();
    const gpuModels = new Set<string>();
    const precisions = new Set<string>();
    const gpuCounts = new Set<string>();
    for (const p of readyProfiles) {
      const spec = p.spec;
      if (spec?.type) optimizationClasses.add(spec.type);
      if (spec?.acceleratorModel) gpuModels.add(spec.acceleratorModel);
      if (spec?.precision) precisions.add(spec.precision);
      if (spec?.acceleratorCount != null)
        gpuCounts.add(String(spec.acceleratorCount));
    }
    return {
      optimizationClasses: Array.from(optimizationClasses).sort(),
      gpuModels: Array.from(gpuModels).sort(),
      precisions: Array.from(precisions).sort(),
      gpuCounts: Array.from(gpuCounts).sort((a, b) => Number(a) - Number(b)),
      profiles: readyProfiles,
    };
  }, [readyProfiles]);

  const hasShownNoProfilesToast = useRef(false);
  const lastResourceName = useRef<string | null>(null);

  // Reset toast shown flag when drawer closes or selected AIM changes
  useEffect(() => {
    if (!isOpen || selectedAim.model !== lastResourceName.current) {
      hasShownNoProfilesToast.current = false;
      lastResourceName.current = selectedAim.model;
    }
  }, [isOpen, selectedAim.model]);

  // Show toast when drawer opens and no profiles are available (successful fetch with 0 profiles or 404).
  // Mirror the profiles-query `enabled` guard so a disabled query (no aimId) is not
  // mistaken for a settled "zero results" fetch.
  useEffect(() => {
    if (
      !isOpen ||
      !selectedAim.aimId ||
      profilesLoading ||
      hasShownNoProfilesToast.current
    ) {
      return;
    }

    const is404 =
      profilesErrorObj instanceof APIRequestError &&
      profilesErrorObj.statusCode === 404;
    const isSuccessWithNoProfiles =
      !profilesError && readyProfiles.length === 0;

    if (is404 || isSuccessWithNoProfiles) {
      toast.error(t('deployAIMDrawer.notifications.noProfilesDescription'));
      hasShownNoProfilesToast.current = true;
    }
  }, [
    isOpen,
    selectedAim.aimId,
    profilesLoading,
    profilesError,
    profilesErrorObj,
    readyProfiles.length,
    toast,
    t,
  ]);

  const huggingFaceTokens =
    projectSecrets?.filter((ps) => ps.useCase === SecretUseCase.HUGGING_FACE) ??
    [];

  const imagePullSecrets =
    projectSecrets?.filter(
      (ps) => ps.useCase === SecretUseCase.IMAGE_PULL_SECRET,
    ) ?? [];

  const createSecretMutation = useMutation({
    mutationFn: (secretRequest: Parameters<typeof createProjectSecret>[1]) =>
      createProjectSecret(namespace, secretRequest),
    onSuccess: (createdSecret: SecretResponseData, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['project', namespace, 'secrets'],
      });

      toast.success(
        t('huggingFaceTokenDrawer.notifications.secretCreated', {
          name: variables.displayName,
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
          displayName: z
            .union([z.literal(''), z.string().min(2).max(253)])
            .optional(),
          selectedToken: z.string().optional(),
          tokenName: z.string().optional(),
          token: z.string().optional(),
          imagePullSecrets: z
            .union([z.string(), z.array(z.string())])
            .transform((val) => (typeof val === 'string' ? [val] : val))
            .optional(),
          metric: z.string().optional(),
          autoscalingEnabled: z.boolean(),
          minReplicas: z.number().min(1).max(30).optional(),
          maxReplicas: z.number().min(1).max(30).optional(),
          metricQuery: z.string().optional(),
          operationOverTime: z.string().optional(),
          targetType: z.string().optional(),
          targetValue: z.number().min(1).optional(),
          optimizationClass: z.string().optional(),
          gpuModel: z.string().optional(),
          precision: z.string().optional(),
          gpuCount: z.string().optional(),
          profileName: z.string().optional(),
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
            displayName: data.displayName || undefined,
            replicas: 1,
          };

          if (hfTokenName) payload.hfToken = hfTokenName;
          if (data.imagePullSecrets && data.imagePullSecrets.length > 0)
            payload.imagePullSecrets = data.imagePullSecrets;
          if (data.metric) payload.metric = data.metric;
          const isExplicit = (v: string | undefined) =>
            !!v && v !== ADVANCED_PARAM_AUTOMATIC;
          if (isExplicit(data.precision)) payload.precision = data.precision;
          if (isExplicit(data.gpuModel)) payload.gpuModel = data.gpuModel;
          if (isExplicit(data.gpuCount)) {
            const count = Number(data.gpuCount);
            if (!Number.isNaN(count) && count >= 1) payload.gpuCount = count;
          }
          if (isExplicit(data.profileName))
            payload.profileName = data.profileName;

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

          await deployInference(namespace, payload);
          // Per-name cluster-catalog cache (['inferenceModel', name]) is stale
          // immediately after deploy — invalidate so re-opening the drawer or
          // the deployed-models list reflects the new service.
          queryClient.invalidateQueries({ queryKey: ['inferenceModel'] });
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
        const createdSecret = await createSecretMutation.mutateAsync(
          createHuggingFaceSecretRequest(tokenName, token),
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

      toast.error(t('huggingFaceTokenDrawer.notifications.noTokenSelected'));
      return;
    },
    [
      namespace,
      selectedAim.model,
      selectedAim.isHfTokenRequired,
      onClose,
      onDeploying,
      t,
      toast,
      queryClient,
      createSecretMutation,
      huggingFaceTokens,
    ],
  );

  const is404 =
    profilesErrorObj instanceof APIRequestError &&
    profilesErrorObj.statusCode === 404;
  // Gate on `selectedAim.aimId` so the form isn't falsely locked while the
  // profiles query is disabled (matches the query's `enabled` predicate).
  const hasNoReadyProfiles =
    !!selectedAim.aimId &&
    !profilesLoading &&
    !profilesError &&
    readyProfiles.length === 0;

  const isDeployDisabled =
    isDeploying || profilesLoading || hasNoReadyProfiles || is404;

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
        model: defaultAim.model,
        displayName: '',
        selectedToken: '',
        tokenName: '',
        token: '',
        imagePullSecrets: [],
        metric: '',
        autoscalingEnabled: false,
        optimizationClass: ADVANCED_PARAM_AUTOMATIC,
        gpuModel: ADVANCED_PARAM_AUTOMATIC,
        precision: ADVANCED_PARAM_AUTOMATIC,
        gpuCount: ADVANCED_PARAM_AUTOMATIC,
        profileName: undefined,
        ...DEFAULT_AUTOSCALING,
      }}
      renderFields={(form) => {
        formRef.current = form;
        const [
          selectedMetric,
          optimizationClass,
          gpuModel,
          precision,
          gpuCount,
        ] = form.watch([
          'metric',
          'optimizationClass',
          'gpuModel',
          'precision',
          'gpuCount',
        ]);
        const filteredProfiles = filterProfilesByAdvancedParams(
          advancedProfileOptions.profiles,
          {
            selectedMetric,
            optimizationClass,
            gpuModel,
            precision,
            gpuCount,
          },
        );
        const noProfileMatches =
          !profilesLoading && filteredProfiles.length === 0;
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
            {(selectedAim?.description.short ||
              selectedAim?.description.full) && (
              <div className="flex items-center gap-1 text-xs text-default-400">
                <IconInfoCircle size={12} className="shrink-0" />
                <span>{t('aimCatalog.card.descriptionDisclaimer')}</span>
              </div>
            )}
            <Divider />
            <div className="text-foreground text-base uppercase font-bold">
              {t('deployAIMDrawer.fields.title')}
            </div>
            <FormInput<DeployAIMFormValues>
              name="displayName"
              form={form}
              label={t('deployAIMDrawer.fields.displayName.title')}
              placeholder={t('deployAIMDrawer.fields.displayName.placeholder')}
            />
            <FormSelect
              label={t('deployAIMDrawer.fields.version.title')}
              name="model"
              form={form}
              aria-label={t('deployAIMDrawer.fields.version.label')}
              placeholder={t('deployAIMDrawer.fields.version.placeholder')}
              onSelectionChange={handleModelChange}
              disabledKeys={aggregatedAim.parsedAIMs
                .filter((v) => v.status !== AIMStatus.READY)
                .map((v) => v.model)}
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
                  <SelectItem key={version.model}>
                    {labels.join(' ')}
                  </SelectItem>
                );
              })}
            </FormSelect>
            {selectedAim.isHfTokenRequired && (
              <>
                <div className="flex items-center gap-1">
                  <h3 className="text-sm text-foreground">
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
            <div className="flex items-center gap-1">
              <h3 className="text-sm text-foreground">
                {t('deployAIMDrawer.fields.imagePullSecrets.title')}
              </h3>
              <Tooltip
                classNames={{
                  content: 'max-w-md whitespace-pre-line',
                }}
                content={t(
                  'deployAIMDrawer.fields.imagePullSecrets.description',
                )}
              >
                <IconInfoCircle
                  className="text-default-400 cursor-pointer"
                  size={16}
                />
              </Tooltip>
            </div>
            <FormSelect
              name="imagePullSecrets"
              form={form}
              selectionMode="multiple"
              aria-label={t('deployAIMDrawer.fields.imagePullSecrets.label')}
              placeholder={t(
                'deployAIMDrawer.fields.imagePullSecrets.placeholder',
              )}
              classNames={{
                trigger: 'min-w-[16rem] w-full',
              }}
              data-testid="deployAimImagePullSecretsSelect"
            >
              {imagePullSecrets.map((secret) => (
                <SelectItem
                  key={secret.metadata.name}
                  textValue={secret.metadata.name}
                  data-testid={`deployAimImagePullSecretOption-${secret.metadata.name}`}
                >
                  {secret.metadata.name}
                </SelectItem>
              ))}
            </FormSelect>
            {metricsWithStatus.length > 0 && (
              <>
                <div className="flex items-center gap-1">
                  <h3 className="text-base font-medium text-foreground">
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
                      {t(getMetricTranslationKey(metric))}
                    </SelectItem>
                  ))}
                </FormSelect>
                <button
                  type="button"
                  onClick={() => setShowAdvancedProfileParams((prev) => !prev)}
                  className={
                    showAdvancedProfileParams
                      ? 'cursor-pointer inline-flex items-center gap-2 rounded-full bg-primary-100 px-3 py-1.5 text-sm font-medium text-primary transition-colors hover:bg-primary-200'
                      : 'cursor-pointer inline-flex items-center gap-2 text-sm font-medium text-primary transition-colors hover:underline'
                  }
                  aria-expanded={showAdvancedProfileParams}
                >
                  {showAdvancedProfileParams ? (
                    <>
                      <IconEyeOff size={18} aria-hidden />
                      {t('deployAIMDrawer.fields.advancedProfileParams.hide')}
                    </>
                  ) : (
                    <>
                      <IconEye size={18} aria-hidden />
                      {t('deployAIMDrawer.fields.advancedProfileParams.show')}
                    </>
                  )}
                </button>
                {showAdvancedProfileParams && (
                  <DeployAIMAdvancedProfileFields
                    form={form}
                    advancedProfileOptions={advancedProfileOptions}
                    filteredProfiles={filteredProfiles}
                    noProfileMatches={noProfileMatches}
                  />
                )}
              </>
            )}

            {/* ====== AUTOSCALING SECTION ====== */}
            <Divider />
            <div className="flex flex-col gap-4">
              {/* Autoscaling Header */}
              <div className="flex items-center gap-1">
                <h3 className="text-base font-medium text-foreground">
                  {t('deployAIMDrawer.fields.autoscaling.title')}
                </h3>
              </div>

              {/* Autoscaling Toggle */}
              <div className="flex flex-col gap-0">
                <FormSwitch
                  form={form}
                  name="autoscalingEnabled"
                  data-testid="autoscaling-toggle"
                >
                  {t('deployAIMDrawer.fields.autoscaling.enable')}
                </FormSwitch>
                <p role="note" className="text-sm text-default-500 ml-[58px]">
                  {t('helper', { ns: 'autoscaling' })}
                </p>
              </div>

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
