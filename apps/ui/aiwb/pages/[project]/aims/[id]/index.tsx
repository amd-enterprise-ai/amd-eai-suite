// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Button,
  Card,
  CardBody,
  CardHeader,
  Select,
  SelectItem,
  ActionButton,
  DateSince,
  HeroMessage,
  Status,
  StatusDisplay,
  Input,
  Accordion,
  AccordionItem,
  Tooltip,
  Skeleton,
} from '@amdenterpriseai/components';
import {
  IconAlertTriangle,
  IconArrowLeft,
  IconCircleCheck,
  IconCopy,
  IconCpu,
  IconDashboard,
  IconDatabase,
  IconFileText,
  IconLink,
  IconMessage,
  IconRefresh,
  IconTrash,
  IconWorld,
} from '@tabler/icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/router';

import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import {
  DOCS_WORKBENCH_BASE,
  WithDocumentationLink,
} from '@amdenterpriseai/utils/app';

import { useSystemToast } from '@amdenterpriseai/hooks';

import {
  aiWorkbenchMenuItems,
  APIRequestError,
} from '@amdenterpriseai/utils/app';
import { get } from 'lodash';
import {
  getAimClusterProfileByName,
  getProjectAimProfileByName,
  getProjectFineTunedModel,
  aimParser,
  getAIMServiceStatusVariants,
  getMetricTranslationKey,
} from '@/lib/app/aims';
import {
  deleteInferenceDeployment,
  getInferenceDeployment,
  getInferenceModel,
  getInferenceReplicas,
  listAllInferenceDeployments,
} from '@/lib/app/inference';
import { getCustomModel } from '@/lib/app/custom-models';
import type { AutoscalingFieldValues } from '@/lib/app/aims';
import type { AIMService, InferenceReplica } from '@/types/aims';
import {
  AIM_PROFILE_TYPE_OPTIMIZED,
  AIMClusterModel,
  AIMModel,
  AIMProfileSpec,
  FINE_TUNED_LABEL,
  NAMESPACE_AIM_MODEL_LABEL,
} from '@/types/aims';
import { useState, useCallback } from 'react';
import AIMConnectModal from '@/components/features/models/AIMConnectModal';
import DeleteWorkloadModal from '@/components/features/workloads/DeleteWorkloadModal';
import WorkloadLogsModal from '@/components/features/workloads/WorkloadLogsModal';
import InferenceMetrics from '@/components/features/workloads/InferenceMetrics';
import { Intent, WorkloadType } from '@amdenterpriseai/types';
import { ResourceType } from '@/types/enums/workloads';
import { AIMServiceStatus } from '@/types/aims';
import { WorkloadStatus } from '@/types/enums/workloads';
import type { ResourceMetrics } from '@/types/projects';
import { useProject } from '@/contexts/ProjectContext';
import { ScalingStatusCard } from '@/components/features/workloads/ScalingStatusCard';
import { SUBMITTER_ANNOTATION_KEY } from '@/components/features/secrets/constants';
import {
  useScalingConvergence,
  CONVERGENCE_POLL_INTERVAL_MS,
} from '@/hooks/useScalingConvergence';
import AIMConditionsList from '@/components/shared/AIMConditionsList';

interface AimDetailsPageProps {
  /** Optional breadcrumb navigation items */
  pageBreadcrumb?: { title: string; href?: string }[];
  /** Unique identifier of the deployed AIM service (workload ID) */
  id: string;
}

type ProfileOverrides = {
  precision?: string;
  metricRaw?: string;
  gpuModel?: string;
  gpuRequestsNum?: number;
};

const extractProfileOverrides = (
  overrides: Record<string, unknown> | undefined,
): ProfileOverrides => {
  const precision =
    typeof overrides?.precision === 'string' ? overrides.precision : undefined;
  const metricRaw =
    typeof overrides?.metric === 'string' ? overrides.metric : undefined;
  const gpuModel =
    typeof overrides?.acceleratorModel === 'string'
      ? overrides.acceleratorModel
      : undefined;
  const rawGpuRequests = overrides?.acceleratorCount;
  const gpuRequestsNum =
    typeof rawGpuRequests === 'number'
      ? rawGpuRequests
      : typeof rawGpuRequests === 'string' &&
          rawGpuRequests !== '' &&
          !Number.isNaN(Number(rawGpuRequests))
        ? Number(rawGpuRequests)
        : undefined;

  return { precision, metricRaw, gpuModel, gpuRequestsNum };
};

/** True when deploy `spec.profileOverrides` carries any profile-related field (used to skip template skeleton). */
const hasDeployProfileOverrides = (o: ProfileOverrides): boolean =>
  Boolean(o.gpuModel) ||
  o.gpuRequestsNum != null ||
  Boolean(o.metricRaw) ||
  Boolean(o.precision);

const toGpuCountLabel = (count: number | undefined): string | undefined =>
  count != null
    ? `${count} ${count === 1 ? 'Accelerator' : 'Accelerators'}`
    : undefined;

/** Appends translated "(automatic)" when the value comes from resolved template metadata, not deploy overrides. */
const formatProfileDetailValue = (
  display: string | undefined,
  isOverride: boolean,
  automaticLabel: string,
): string => {
  if (display == null || display === '') return '—';
  if (isOverride) return display;
  return `${display} ${automaticLabel}`;
};

const AimDetailsPage: React.FC<AimDetailsPageProps> & WithDocumentationLink = ({
  id,
}) => {
  const { t } = useTranslation([
    'workloads',
    'common',
    'autoscaling',
    'models',
  ]);
  const router = useRouter();
  const queryClient = useQueryClient();
  const { toast } = useSystemToast();
  const [isLogsModalOpen, setIsLogsModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isConnectModalOpen, setIsConnectModalOpen] = useState(false);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isPollingForConvergence, setIsPollingForConvergence] = useState(false);
  const [selectedReplica, setSelectedReplica] = useState<string>('all');
  const {
    activeProject: namespace,
    projectPath,
    projectUrl,
    aiGatewayEnabled,
    aiGatewayUrl,
  } = useProject();

  const {
    data: aimService,
    isLoading: isLoadingAimService,
    isError: isAimServiceError,
    error: aimServiceError,
    refetch: refetchAimService,
  } = useQuery({
    queryKey: ['aimService', namespace, id],
    queryFn: () => getInferenceDeployment(namespace as string, id as string),
    enabled: !!namespace && !!id && !isDeleting,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    refetchInterval: isPollingForConvergence
      ? CONVERGENCE_POLL_INTERVAL_MS
      : false,
    // Skip retries on 404 so the deleted-history fallback below runs immediately.
    retry: (failureCount, error) =>
      !(error instanceof APIRequestError && error.statusCode === 404) &&
      failureCount < 3,
  });

  const stopConvergencePolling = useCallback(
    () => setIsPollingForConvergence(false),
    [],
  );
  const handleConvergenceTimeout = useCallback(() => {
    setIsPollingForConvergence(false);
    toast.warning(t('autoscaling:notifications.convergenceTimeout'));
  }, [toast, t]);

  const { startPolling } = useScalingConvergence({
    aimService,
    isAimServiceError,
    isPolling: isPollingForConvergence,
    onConverged: stopConvergencePolling,
    onTimeout: handleConvergenceTimeout,
  });

  const liveQuery404 =
    aimServiceError instanceof APIRequestError &&
    aimServiceError.statusCode === 404;

  // The history query walks the entire Deleted list via fetchAllPages — gate it
  // on liveQuery404 so live-AIM visits don't pay that cost.
  const { data: aimServiceHistory, isLoading: isLoadingAimServiceHistory } =
    useQuery({
      queryKey: ['aimServiceHistory', namespace, id],
      queryFn: () =>
        listAllInferenceDeployments(namespace as string, {
          statusFilter: [AIMServiceStatus.DELETED],
        }),
      enabled: !!namespace && !!id && !isDeleting && liveQuery404,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
    });

  const historicalService: AIMService | undefined = aimServiceHistory?.find(
    (h) => h.id === id,
  );

  // The AIMClusterModel/AIMModel resource name. AIWB always sets
  // `spec.model.name` at create time; the backend (`AIMServiceResource`)
  // backfills it from `status.resolvedModel.name` for legacy v1alpha1
  // deploy-by-image services where the user only set `spec.model.image`.
  const resourceName =
    aimService?.spec?.model?.name || historicalService?.spec?.model?.name;

  const _isHistorical = !aimService && !!historicalService;

  const isFinetunedModel =
    aimService?.metadata?.labels?.[FINE_TUNED_LABEL] === 'true';

  const isCustomModel =
    aimService?.metadata?.labels?.[NAMESPACE_AIM_MODEL_LABEL] === 'true';

  // The cluster-model branch shares its cache with useInferenceModelsByName via
  // ['inferenceModel', resourceName] so list pages and this details page resolve to a
  // single fetch per name. The fine-tuned, custom-model, and historical-fallback branches
  // keep their namespace-scoped key because they hit different endpoints.
  const clusterModelQueryKey = ['inferenceModel', resourceName] as const;
  const finetunedQueryKey = [
    'aim',
    namespace,
    id,
    resourceName,
    isFinetunedModel,
  ] as const;
  const customModelQueryKey = ['customModel', namespace, resourceName] as const;
  const {
    data: aimClusterModel,
    isLoading: isLoadingAim,
    isError: isAimError,
  } = useQuery<AIMClusterModel | AIMModel>({
    queryKey:
      isFinetunedModel || _isHistorical
        ? finetunedQueryKey
        : isCustomModel
          ? customModelQueryKey
          : clusterModelQueryKey,
    queryFn: async () => {
      if (isFinetunedModel) {
        return getProjectFineTunedModel(
          resourceName as string,
          namespace as string,
        );
      }
      if (isCustomModel) {
        // Custom (BYOM) models are namespace-scoped AIMModels; their detail
        // data lives on the custom-models endpoint, not the cluster catalog.
        return getCustomModel(
          namespace as string,
          resourceName as string,
        ) as unknown as AIMModel;
      }
      // For historical services isFinetunedModel is always false (aimService is gone).
      // Try cluster-scoped first; if it 404s, the model was namespace-scoped (finetuned or custom).
      if (_isHistorical) {
        try {
          return await getInferenceModel(resourceName as string);
        } catch {
          return getProjectFineTunedModel(
            resourceName as string,
            namespace as string,
          );
        }
      }
      return getInferenceModel(resourceName as string);
    },
    enabled:
      !!resourceName && (!isFinetunedModel || !!namespace) && !isDeleting,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
  });

  const { data: replicas } = useQuery<InferenceReplica[]>({
    queryKey: ['inferenceReplicas', namespace, id],
    queryFn: () => getInferenceReplicas(namespace as string, id as string),
    enabled:
      !!namespace &&
      !!id &&
      !isDeleting &&
      [AIMServiceStatus.RUNNING, AIMServiceStatus.DEGRADED].includes(
        aimService?.status?.status as AIMServiceStatus,
      ),
    refetchOnWindowFocus: false,
  });

  const resolvedProfile = aimService?.status?.resolvedProfile;
  const resolvedProfileName = resolvedProfile?.name ?? null;
  const isNamespaceScoped = resolvedProfile?.scope === 'Namespace';
  const { data: resolvedProfileResource } = useQuery({
    queryKey: isNamespaceScoped
      ? (['aim-profile', 'project', namespace, resolvedProfileName] as const)
      : (['aim-profile', 'cluster', resolvedProfileName] as const),
    queryFn: () =>
      isNamespaceScoped
        ? getProjectAimProfileByName(namespace as string, resolvedProfileName!)
        : getAimClusterProfileByName(resolvedProfileName!),
    enabled: !!resolvedProfileName && (!isNamespaceScoped || !!namespace),
    staleTime: Infinity,
  });
  const resolvedProfileSpec: AIMProfileSpec | null =
    resolvedProfileResource?.spec ?? null;

  const isMetricUnoptimized =
    !!resolvedProfileSpec &&
    resolvedProfileSpec.type !== AIM_PROFILE_TYPE_OPTIMIZED;

  const { mutate: deleteWorkloadMutation } = useMutation({
    mutationFn: (serviceId: string) => {
      setIsDeleting(true);
      return deleteInferenceDeployment(namespace!, serviceId);
    },
    onSuccess: () => {
      queryClient.removeQueries({
        queryKey: ['aimService', namespace, id],
      });
      toast.success(t('list.actions.delete.notification.success'));
      router.push(projectPath('/models'));
    },
    onError: () => {
      setIsDeleting(false);
      toast.error(t('list.actions.delete.notification.error'));
    },
  });

  const handleSettingsSaved = useCallback(
    (savedValues: AutoscalingFieldValues) => {
      setIsPollingForConvergence(true);
      startPolling(savedValues);
      refetchAimService();
    },
    [startPolling, refetchAimService],
  );

  const handleBack = () => {
    router.back();
  };

  // History only starts loading after the live query 404s, so the two loading
  // flags must be ORed (not ANDed) — sequenced via liveQuery404.
  const isLoadingFirstQuery =
    isLoadingAimService || (liveQuery404 && isLoadingAimServiceHistory);
  const isLoadingSecondQuery =
    !!resourceName && !aimClusterModel && !isAimError;
  const isLoading = isLoadingFirstQuery || isLoadingSecondQuery;

  if (isLoading) {
    return (
      <div className="flex flex-col space-y-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Skeleton className="h-8 w-8 rounded-lg" />
            <div className="flex items-center space-x-3 pr-2">
              <Skeleton className="h-7 w-64 rounded-lg" />
              <Skeleton className="h-6 w-24 rounded-full" />
            </div>
          </div>
        </div>
        <Skeleton className="h-6 w-64 rounded-lg" />
        <div className="columns-1 md:columns-2 xl:columns-3 gap-6 space-y-6">
          <Skeleton className="h-64 w-full rounded-lg" />
          <Skeleton className="h-64 w-full rounded-lg" />
          <Skeleton className="h-64 w-full rounded-lg" />
        </div>
      </div>
    );
  }

  // A live error that isn't recovered by a historical lookup is the error path.
  const hasServiceError = isAimServiceError && !_isHistorical;
  const hasAimError = isAimError || !aimClusterModel;

  if ((hasServiceError && !isLoading) || hasAimError) {
    return (
      <HeroMessage
        intent={Intent.DANGER}
        title={t('errors.workloadNotFound.title')}
        description={t('errors.workloadNotFound.description', {
          project: namespace,
        })}
        endContent={
          <ActionButton
            className="mt-4"
            onPress={() => router.reload()}
            icon={<IconRefresh size={18} />}
          >
            {t('common:error.refreshActionLabel')}
          </ActionButton>
        }
      />
    );
  }

  const handleCopyToClipboard = (text: string, fieldName: string) => {
    if (!navigator.clipboard) return;

    navigator.clipboard.writeText(text).then(() => {
      setCopiedField(fieldName);
      setTimeout(() => {
        setCopiedField(null);
      }, 2000);
    });
  };

  // Deleted/historical entries arrive as standard AIMServiceResponse shapes
  // (synthesized from the DB row), so the regular aimParser handles both live
  // and historical services uniformly.
  const parsedAim = aimParser(
    aimClusterModel,
    aimService
      ? [aimService]
      : historicalService
        ? [historicalService]
        : undefined,
  );
  const deployedService = parsedAim.deployedService;

  const specOverrides = deployedService?.spec?.profileOverrides as
    | Record<string, unknown>
    | undefined;
  const profileOverrides = extractProfileOverrides(specOverrides);

  const hasProfileDataFromSpec = hasDeployProfileOverrides(profileOverrides);
  const {
    precision: overridePrecision,
    metricRaw: overrideMetricRaw,
    gpuModel: overrideGpuModel,
    gpuRequestsNum: overrideGpuRequestsNum,
  } = profileOverrides;

  const profileSpec = resolvedProfileSpec;
  const profileGpuDisplay = overrideGpuModel ?? profileSpec?.acceleratorModel;
  const profileGpuCountDisplay =
    toGpuCountLabel(overrideGpuRequestsNum) ??
    toGpuCountLabel(profileSpec?.acceleratorCount);
  const profileMetricKey = overrideMetricRaw ?? profileSpec?.metric;
  const profileMetricDisplay = profileMetricKey
    ? t(getMetricTranslationKey(String(profileMetricKey)), { ns: 'models' })
    : undefined;
  const profilePrecisionDisplay = overridePrecision ?? profileSpec?.precision;

  const isMetricOverride = Boolean(overrideMetricRaw);
  const isGpuOverride = Boolean(overrideGpuModel);
  const isGpuCountOverride = overrideGpuRequestsNum != null;
  const isPrecisionOverride = Boolean(overridePrecision);

  const profileAutomaticLabel = t('details.profile.automatic');

  const aimConditions = deployedService?.status?.conditions;
  const { external, internal } = deployedService?.endpoints || {};
  const externalHost = external ? `${external}/v1/chat/completions` : '';
  const internalHost = internal ? `${internal}/v1/chat/completions` : '';

  // When the unified Envoy AI Gateway is enabled and configured, inference goes
  // through a single endpoint (the model is selected via the OpenAI `model`
  // field), shown in place of the per-service external host.
  const gatewayHost =
    aiGatewayEnabled && aiGatewayUrl
      ? `${aiGatewayUrl.replace(/\/$/, '')}/v1/chat/completions`
      : '';
  const useGateway = !!gatewayHost;

  const workloadCreatedBy =
    deployedService?.metadata?.annotations?.[SUBMITTER_ANNOTATION_KEY] || null;

  // Construct workload object for WorkloadLogsModal
  const aimWorkload: ResourceMetrics = {
    id,
    name: parsedAim.model,
    displayName: parsedAim.title || parsedAim.model,
    type: WorkloadType.INFERENCE,
    status:
      (deployedService?.status.status as unknown as WorkloadStatus) ??
      WorkloadStatus.UNKNOWN,
    gpuCount: null,
    templateGpuCount: null,
    gpu: null,
    acceleratorType: null,
    metric: null,
    precision: null,
    vram: null,
    createdAt: deployedService?.metadata?.creationTimestamp ?? null,
    createdBy: workloadCreatedBy,
    resourceType: ResourceType.AIM_SERVICE,
  };

  // Show only "{*}Ready" conditions, filter out anything else.
  const hasConditions = (aimConditions ?? []).some(
    (c) => c.type !== 'Ready' && c.type?.endsWith('Ready'),
  );

  return (
    <div className="flex flex-col space-y-6 py-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <ActionButton
            secondary
            onPress={handleBack}
            size="sm"
            icon={<IconArrowLeft size={16} />}
          />
          <div className="flex items-center space-x-3 pr-2">
            <h2>
              {isFinetunedModel ? parsedAim.title : parsedAim.canonicalName}
            </h2>
            <StatusDisplay
              type={deployedService?.status.status as string}
              variants={getAIMServiceStatusVariants(t)}
              additionalProps={{ isShowBackground: true, isTextColored: true }}
            />
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center space-x-2">
          {replicas && replicas.length > 1 && (
            <Select
              size="sm"
              className="w-48"
              selectedKeys={[selectedReplica]}
              onSelectionChange={(keys) => {
                const selectedKey = Array.from(keys)[0] as string;
                if (selectedKey !== undefined) setSelectedReplica(selectedKey);
              }}
              aria-label={t('details.metrics.replicaSelector.label')}
            >
              {[
                {
                  key: 'all',
                  label: t('details.metrics.replicaSelector.allReplicas'),
                },
                ...replicas.map((r) => ({
                  key: r.metadata.name,
                  label: r.metadata.name.split('-').at(-1) ?? r.metadata.name,
                  fullName: r.metadata.name,
                })),
              ].map((opt) => (
                <SelectItem key={opt.key} textValue={opt.label}>
                  {'fullName' in opt ? (
                    <Tooltip content={opt.fullName} placement="right">
                      <span>{opt.label}</span>
                    </Tooltip>
                  ) : (
                    opt.label
                  )}
                </SelectItem>
              ))}
            </Select>
          )}
          <ActionButton
            secondary
            onPress={() =>
              router.push({
                pathname: projectPath('/chat'),
                query: { workload: id },
              })
            }
            icon={<IconMessage size={16} />}
            isDisabled={
              deployedService?.status.status !== AIMServiceStatus.RUNNING
            }
          >
            {t('list.actions.chat.label')}
          </ActionButton>

          <ActionButton
            secondary
            onPress={() => setIsLogsModalOpen(true)}
            icon={<IconFileText size={16} />}
          >
            {t('list.actions.logs.label')}
          </ActionButton>

          <ActionButton
            secondary
            color="danger"
            onPress={() => setIsDeleteModalOpen(true)}
            icon={<IconTrash size={16} />}
            isDisabled={
              deployedService?.status.status === AIMServiceStatus.DELETED
            }
          >
            {t('list.actions.delete.label')}
          </ActionButton>
        </div>
      </div>

      {/* Inference metrics */}
      {deployedService?.status.status &&
        !_isHistorical &&
        [
          AIMServiceStatus.STARTING,
          AIMServiceStatus.RUNNING,
          AIMServiceStatus.DEGRADED,
        ].includes(deployedService.status.status) && (
          <InferenceMetrics
            workloadId={id}
            podName={selectedReplica === 'all' ? undefined : selectedReplica}
          />
        )}

      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">{t('list.headers.aim.title')}</h3>
      </div>

      {/* Autoscaling Status Card - own row, spans 2 of 3 columns at xl */}
      {aimService?.spec?.autoScaling && (
        <div className="w-full xl:w-[calc((200%_-_1.5rem)_/_3)]">
          <ScalingStatusCard
            spec={aimService.spec}
            runtime={aimService.status.runtime}
            namespace={namespace ?? undefined}
            id={id}
            onSettingsSaved={handleSettingsSaved}
            replicas={replicas}
          />
        </div>
      )}

      <div className="columns-1 md:columns-2 xl:columns-3 gap-6 space-y-6">
        {/* AIM Information + Profile (stacked under basic information) */}
        {(aimClusterModel || isLoadingAim) && (
          <div className="break-inside-avoid mb-6 flex flex-col gap-6">
            <Card className="border-1 border-default-200 shadow-sm">
              <CardHeader className="flex items-center px-4 py-3">
                <h3 className="text-base font-semibold flex items-center space-x-2">
                  <IconDatabase size={16} className="text-default-500" />
                  <span>{t('details.sections.basicInformation')}</span>
                </h3>
              </CardHeader>
              <CardBody className="space-y-3 px-4 pb-4 pt-0">
                {isLoadingAim ? (
                  <div className="flex flex-col space-y-3">
                    <Skeleton className="w-full h-6 rounded-lg" />
                    <Skeleton className="w-3/4 h-6 rounded-lg" />
                    <Skeleton className="w-2/3 h-6 rounded-lg" />
                    <Skeleton className="w-1/2 h-6 rounded-lg" />
                  </div>
                ) : (
                  <div className="flex flex-col space-y-3">
                    {aimClusterModel!.spec.image && (
                      <div className="flex items-center space-x-3">
                        <div>
                          <h5 className="text-sm text-default-700">
                            {t('list.headers.aim.image')}
                          </h5>
                          <p className="font-mono text-sm">
                            {aimClusterModel!.spec.image}
                          </p>
                        </div>
                      </div>
                    )}

                    {parsedAim.imageVersion && (
                      <div className="flex items-center space-x-3">
                        <div>
                          <h5 className="text-sm text-default-700">
                            {t('list.headers.aim.containerVersion')}
                          </h5>
                          <p className="font-mono text-sm">
                            {parsedAim.imageVersion}
                          </p>
                        </div>
                      </div>
                    )}

                    <div className="flex items-center space-x-3">
                      <div>
                        <h5 className="text-sm text-default-700">
                          {t('list.headers.aim.resourceName')}
                        </h5>
                        <p className="font-mono text-sm">
                          {parsedAim.model || '—'}
                        </p>
                      </div>
                    </div>

                    {parsedAim.canonicalName && (
                      <div className="flex items-center space-x-3">
                        <div>
                          <h5 className="text-sm text-default-700">
                            {t(
                              isFinetunedModel
                                ? 'list.headers.aim.baseModel'
                                : 'list.headers.aim.canonicalName',
                            )}
                          </h5>
                          <p className="font-mono text-sm">
                            {parsedAim.canonicalName}
                          </p>
                        </div>
                      </div>
                    )}

                    {aimClusterModel!.status?.imageMetadata?.oci
                      ?.description && (
                      <div className="flex items-center space-x-3">
                        <div>
                          <h5 className="text-sm text-default-700">
                            {t('list.headers.aim.description')}
                          </h5>
                          <p className="text-sm">
                            {
                              aimClusterModel!.status.imageMetadata.oci
                                .description
                            }
                          </p>
                        </div>
                      </div>
                    )}

                    <div className="flex items-center space-x-3">
                      <div>
                        <h5 className="text-sm text-default-700">
                          {t('list.headers.aim.id')}
                        </h5>
                        <p className="font-mono text-sm">{id}</p>
                      </div>
                    </div>
                  </div>
                )}
              </CardBody>
            </Card>

            <Card className="border-1 border-default-200 shadow-sm">
              <CardHeader className="flex items-center gap-3 px-4 py-3">
                <IconCpu
                  size={18}
                  className="shrink-0 text-default-500"
                  aria-hidden
                />
                <h3 className="text-base font-semibold">
                  {t('details.profile.title')}
                </h3>
              </CardHeader>
              <CardBody className="space-y-4 px-4 pb-4 pt-0">
                {isLoadingAim ? (
                  <div className="flex flex-col space-y-3">
                    <Skeleton className="h-4 w-full rounded-lg" />
                    <Skeleton className="h-4 w-full rounded-lg" />
                    <Skeleton className="h-4 w-full rounded-lg" />
                    <Skeleton className="h-4 w-full rounded-lg" />
                  </div>
                ) : (
                  <>
                    <div className="space-y-3">
                      <div>
                        <h5 className="text-sm text-default-700">
                          {t('details.profile.performanceMetric')}
                        </h5>
                        <p className="font-mono text-sm">
                          {formatProfileDetailValue(
                            profileMetricDisplay,
                            isMetricOverride,
                            profileAutomaticLabel,
                          )}
                        </p>
                      </div>
                      <div>
                        <h5 className="text-sm text-default-700">
                          {t('details.profile.accelerator')}
                        </h5>
                        <p className="font-mono text-sm">
                          {formatProfileDetailValue(
                            profileGpuDisplay,
                            isGpuOverride,
                            profileAutomaticLabel,
                          )}
                        </p>
                      </div>
                      <div>
                        <h5 className="text-sm text-default-700">
                          {t('details.profile.acceleratorCount')}
                        </h5>
                        <p className="font-mono text-sm">
                          {formatProfileDetailValue(
                            profileGpuCountDisplay,
                            isGpuCountOverride,
                            profileAutomaticLabel,
                          )}
                        </p>
                      </div>
                      <div>
                        <h5 className="text-sm text-default-700">
                          {t('details.profile.precision')}
                        </h5>
                        <p className="font-mono text-sm">
                          {formatProfileDetailValue(
                            profilePrecisionDisplay,
                            isPrecisionOverride,
                            profileAutomaticLabel,
                          )}
                        </p>
                      </div>
                    </div>
                    {isMetricUnoptimized && (
                      <div className="border-t border-default-100 pt-4">
                        <div className="flex items-start gap-1.5">
                          <IconAlertTriangle
                            size={14}
                            className="mt-0.5 shrink-0 text-warning"
                            aria-hidden
                          />
                          <p className="text-tiny text-default-500">
                            {t('details.profile.unoptimizedNotice')}
                          </p>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </CardBody>
            </Card>
          </div>
        )}
        {/* Status */}
        <Card className="break-inside-avoid mb-6 border-1 border-default-200 shadow-sm">
          <CardHeader className="flex items-center px-4 py-3">
            <h3 className="text-base font-semibold flex items-center space-x-2">
              <IconDashboard size={16} className="text-default-500" />
              <span>{t('details.sections.status')}</span>
            </h3>
          </CardHeader>
          <CardBody className="px-4 pb-4 pt-0">
            <div className="mb-4 space-y-3 border-b border-default-100 pb-4">
              <div className="flex items-center space-x-3">
                <div>
                  <h5 className="text-sm text-default-700">
                    {t('list.headers.createdBy.title')}
                  </h5>
                  <p className="text-sm">{workloadCreatedBy ?? '—'}</p>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <div>
                  <h5 className="text-sm text-default-700">
                    {t('list.headers.createdAt.title')}
                  </h5>
                  {deployedService?.metadata?.creationTimestamp ? (
                    <DateSince
                      date={deployedService.metadata.creationTimestamp}
                      className="text-sm text-foreground"
                    />
                  ) : (
                    <p className="text-sm">—</p>
                  )}
                </div>
              </div>
            </div>
            {hasConditions ? (
              <Accordion className="px-0">
                <AccordionItem
                  title={
                    <StatusDisplay
                      type={deployedService?.status.status as string}
                      variants={getAIMServiceStatusVariants(t)}
                    />
                  }
                  classNames={{
                    trigger: 'py-2',
                    content: 'pt-2',
                  }}
                >
                  <AIMConditionsList conditions={aimConditions ?? []} />
                </AccordionItem>
              </Accordion>
            ) : (
              <StatusDisplay
                type={deployedService?.status.status as string}
                variants={getAIMServiceStatusVariants(t)}
              />
            )}
          </CardBody>
        </Card>
        {/* Output Information */}
        {(useGateway || externalHost || internalHost) && (
          <Card className="break-inside-avoid mb-6 border-1 border-default-200 shadow-sm">
            <CardHeader className="flex items-center justify-between px-4 py-3">
              <h3 className="text-base font-semibold flex items-center space-x-2">
                <IconWorld size={16} className="text-default-500" />
                <span>{t('details.sections.output')}</span>
              </h3>
              <Button
                data-testid="connect-to-model-button"
                size="sm"
                variant="light"
                startContent={<IconLink size={14} />}
                onPress={() => setIsConnectModalOpen(true)}
              >
                {t('models:aimCatalog.actions.connect.label')}
              </Button>
            </CardHeader>
            <CardBody className="space-y-2 px-4 pb-4 pt-0">
              {useGateway ? (
                <div className="space-y-2">
                  <h5 className="text-sm text-default-700">
                    {t('models:aimCatalog.actions.connect.modal.inferenceUrl')}
                  </h5>
                  <Input
                    value={gatewayHost}
                    readOnly
                    variant="bordered"
                    classNames={{
                      input: 'font-mono text-sm',
                    }}
                    endContent={
                      <ActionButton
                        tertiary
                        size="sm"
                        onPress={() =>
                          handleCopyToClipboard(gatewayHost, 'inferenceUrl')
                        }
                        icon={
                          copiedField === 'inferenceUrl' ? (
                            <IconCircleCheck
                              size={16}
                              className="text-success"
                            />
                          ) : (
                            <IconCopy size={16} />
                          )
                        }
                      />
                    }
                  />
                </div>
              ) : (
                externalHost && (
                  <div className="space-y-2">
                    <h5 className="text-sm text-default-700">
                      {t('details.fields.externalHost')}
                    </h5>
                    <Input
                      value={externalHost}
                      readOnly
                      variant="bordered"
                      classNames={{
                        input: 'font-mono text-sm',
                      }}
                      endContent={
                        <ActionButton
                          tertiary
                          size="sm"
                          onPress={() =>
                            handleCopyToClipboard(externalHost, 'externalHost')
                          }
                          icon={
                            copiedField === 'externalHost' ? (
                              <IconCircleCheck
                                size={16}
                                className="text-success"
                              />
                            ) : (
                              <IconCopy size={16} />
                            )
                          }
                        />
                      }
                    />
                  </div>
                )
              )}

              {internalHost && (
                <div className="space-y-2">
                  <h5 className="text-sm text-default-700">
                    {t('details.fields.internalHost')}
                  </h5>
                  <Input
                    value={internalHost}
                    readOnly
                    variant="bordered"
                    classNames={{
                      input: 'font-mono text-sm',
                    }}
                    endContent={
                      <ActionButton
                        tertiary
                        size="sm"
                        onPress={() =>
                          handleCopyToClipboard(internalHost, 'internalHost')
                        }
                        icon={
                          copiedField === 'internalHost' ? (
                            <IconCircleCheck
                              size={16}
                              className="text-success"
                            />
                          ) : (
                            <IconCopy size={16} />
                          )
                        }
                      />
                    }
                  />
                </div>
              )}
            </CardBody>
          </Card>
        )}
      </div>

      {/* Modals */}
      <DeleteWorkloadModal
        isOpen={isDeleteModalOpen}
        onOpenChange={setIsDeleteModalOpen}
        workload={aimWorkload}
        onConfirmAction={deleteWorkloadMutation}
      />

      {isLogsModalOpen && (
        <WorkloadLogsModal
          isOpen={isLogsModalOpen}
          onOpenChange={setIsLogsModalOpen}
          workload={aimWorkload}
          namespace={namespace as string}
        />
      )}

      {isConnectModalOpen && (
        <AIMConnectModal
          isOpen={isConnectModalOpen}
          onOpenChange={setIsConnectModalOpen}
          endpoints={deployedService?.endpoints}
          modelName={deployedService?.status?.resolvedModel?.name}
          serviceId={deployedService?.id ?? undefined}
          onChatRequested={(serviceId) => {
            router.push({
              pathname: projectPath('/chat'),
              query: { workload: serviceId },
            });
          }}
        />
      )}
    </div>
  );
};

export async function getServerSideProps(context: {
  locale: any;
  params: any;
  query: any;
}) {
  const { locale, params, query } = context;

  const id = params?.id;
  const project = params?.project as string;

  if (!id) {
    return {
      redirect: {
        destination: `/${project}/models`,
        permanent: false,
      },
    };
  }

  const translations = await serverSideTranslations(locale, [
    'common',
    'workloads',
    'models',
    'autoscaling',
    'projects',
  ]);

  let breadcrumb: { title: string; href?: string }[] = [
    {
      title:
        translations._nextI18Next?.initialI18nStore[locale]?.workloads?.details
          ?.breadcrumb || 'Workload details',
    },
  ];

  // Determine previous route from referer query param for correct parent breadcrumb
  const refererRoutePath = query?.ref || '/';
  const prevNavItem = aiWorkbenchMenuItems.find(
    (item) => item.href === refererRoutePath,
  );

  if (prevNavItem) {
    const title = get(
      translations._nextI18Next?.initialI18nStore[locale]?.common,
      prevNavItem.stringKey,
      prevNavItem.stringKey,
    );

    breadcrumb = [
      {
        title,
        href: `/${project}${prevNavItem.href}`,
      },
      ...breadcrumb,
    ];
  }

  return {
    props: {
      ...translations,
      pageBreadcrumb: breadcrumb,
      id,
    },
  };
}

export default AimDetailsPage;

AimDetailsPage.documentationLink = `${DOCS_WORKBENCH_BASE}/models.html`;
