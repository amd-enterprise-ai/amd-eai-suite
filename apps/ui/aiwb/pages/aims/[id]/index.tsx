// Copyright © Advanced Micro Devices, Inc., or its affiliates.
//
// SPDX-License-Identifier: MIT

import {
  Card,
  CardBody,
  CardHeader,
  Skeleton,
  Input,
  Accordion,
  AccordionItem,
} from '@heroui/react';
import {
  IconAlertTriangle,
  IconArrowLeft,
  IconCircleCheck,
  IconClock,
  IconCopy,
  IconDashboard,
  IconDatabase,
  IconFileText,
  IconMessage,
  IconRefresh,
  IconTrash,
  IconWorld,
} from '@tabler/icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/router';

import { getServerSession } from 'next-auth';
import { useTranslation } from 'next-i18next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import { authOptions } from '@amdenterpriseai/utils/server';

import { useSystemToast } from '@amdenterpriseai/hooks';

import {
  ActionButton,
  DateDisplay,
  HeroMessage,
  Status,
  StatusDisplay,
} from '@amdenterpriseai/components';

import {
  aiWorkbenchMenuItems,
  APIRequestError,
  displayTimestamp,
} from '@amdenterpriseai/utils/app';
import { get } from 'lodash';
import {
  getAimByResourceName,
  getAimService,
  getAimServiceTemplates,
  aimParser,
  getAIMServiceStatusVariants,
  undeployAim,
  getAimServiceHistory,
  historicalAimParser,
} from '@/lib/app/aims';
import {
  AIMClusterServiceTemplate,
  AIMServiceCondition,
  AIMServiceStatus,
  AIMMetric,
  AIMServiceHistoryResponse,
} from '@/types/aims';
import { useState } from 'react';
import { UnoptimizedProfileBadge } from '@/components/features/models/UnoptimizedProfileBadge';
import DeleteWorkloadModal from '@/components/features/workloads/DeleteWorkloadModal';
import WorkloadLogsModal from '@/components/features/workloads/WorkloadLogsModal';
import { LogSource } from '@/components/features/workloads/WorkloadLogs';
import InferenceMetrics from '@/components/features/workloads/InferenceMetrics';
import {
  ResourceType,
  Intent,
  WorkloadStatus,
  WorkloadType,
} from '@amdenterpriseai/types/src';
import type { ResourceMetrics } from '@/types/namespaces';
import { useProject } from '@/contexts/ProjectContext';
import { ScalingStatusCard } from '@/components/features/workloads/ScalingStatusCard';

interface AimDetailsPageProps {
  /** Optional breadcrumb navigation items */
  pageBreadcrumb?: { title: string; href?: string }[];
  /** Unique identifier of the deployed AIM service (workload ID) */
  id: string;
}

enum ConditionStatus {
  READY = 'ready',
  FAILED = 'failed',
  PENDING = 'pending',
}

/**
 * Determines the status of a condition based on its type, status, and reason.
 * - Ready: type ends with "Ready" and status is "True"
 * - Failed: type ends with "Ready" and status is "False" and reason ends with "Failed"
 * - Pending: everything else
 */
const getConditionStatus = (
  condition: AIMServiceCondition,
): ConditionStatus => {
  const isReadyType = condition.type.endsWith('Ready');
  if (isReadyType && condition.status === 'True') {
    return ConditionStatus.READY;
  }
  if (
    isReadyType &&
    condition.status === 'False' &&
    condition.reason.endsWith('Failed')
  ) {
    return ConditionStatus.FAILED;
  }
  return ConditionStatus.PENDING;
};

const getConditionStatusProps = (
  status: ConditionStatus,
  t: (key: string) => string,
) => {
  const configs = {
    [ConditionStatus.READY]: {
      label: t('details.conditions.ready'),
      intent: Intent.SUCCESS,
    },
    [ConditionStatus.FAILED]: {
      label: t('details.conditions.failed'),
      intent: Intent.DANGER,
    },
    [ConditionStatus.PENDING]: {
      label: t('details.conditions.pending'),
      intent: Intent.WARNING,
      icon: IconClock, // Override to use clock instead of spinner
    },
  };
  return configs[status] || configs[ConditionStatus.PENDING];
};

/**
 * To sort the conditions by status.
 * Failed → Pending → Ready
 */
const statusOrder = {
  [ConditionStatus.FAILED]: 0,
  [ConditionStatus.PENDING]: 1,
  [ConditionStatus.READY]: 2,
};

const AimDetailsPage: React.FC<AimDetailsPageProps> = ({ id }) => {
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
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const { activeProject: namespace } = useProject();

  const {
    data: aimService,
    isLoading: isLoadingAimService,
    isError: isAimServiceError,
    error: aimServiceError,
    refetch: refetchAimService,
  } = useQuery({
    queryKey: ['aimService', namespace, id],
    queryFn: () => getAimService(namespace as string, id as string),
    enabled: !!namespace && !!id && !isDeleting,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
  });

  const {
    data: aimServiceHistory,
    isLoading: isLoadingAimServiceHistory,
    isError: isAimServiceHistoryError,
  } = useQuery({
    queryKey: ['aimServiceHistory', namespace, id],
    queryFn: () => getAimServiceHistory(namespace as string),
    enabled: !!namespace && !!id && !isDeleting,
    select: (data: AIMServiceHistoryResponse[]) =>
      data.filter((s) => s.status === AIMServiceStatus.DELETED),
    refetchOnWindowFocus: false,
    refetchOnMount: false,
  });

  const historicalService = aimServiceHistory?.find((h) => h.id === id)!;

  const resourceName =
    aimService?.status?.resolvedModel?.name || historicalService?.model;

  const _isNotFoundError =
    (aimServiceError as APIRequestError)?.statusCode === 404;
  const _isHistorical = !aimService && !!historicalService;

  const {
    data: aimClusterModel,
    isLoading: isLoadingAim,
    isError: isAimError,
  } = useQuery({
    queryKey: ['aim', namespace, id, resourceName],
    queryFn: () => getAimByResourceName(resourceName as string),
    enabled: !!resourceName && !isDeleting,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
  });

  const { data: serviceTemplates, isLoading: templatesLoading } = useQuery<
    AIMClusterServiceTemplate[]
  >({
    queryKey: ['aim-templates', resourceName],
    queryFn: () => getAimServiceTemplates(resourceName as string),
    enabled: !!resourceName && !isDeleting,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
  });

  const resolvedTemplateName =
    aimService?.status?.resolvedTemplate?.name ?? undefined;
  const resolvedTemplate = (serviceTemplates ?? []).find(
    (t) => t.metadata?.name === resolvedTemplateName,
  );
  const profileType = resolvedTemplate?.status?.profile?.metadata?.type;
  const isMetricUnoptimized = resolvedTemplate && profileType !== 'optimized';

  const { mutate: deleteWorkloadMutation } = useMutation({
    mutationFn: (serviceId: string) => {
      setIsDeleting(true);
      return undeployAim(namespace!, serviceId);
    },
    onSuccess: () => {
      queryClient.removeQueries({
        queryKey: ['aimService', namespace, id],
      });
      toast.success(t('list.actions.delete.notification.success'));
      router.push('/models');
    },
    onError: () => {
      setIsDeleting(false);
      toast.error(t('list.actions.delete.notification.error'));
    },
  });

  const handleBack = () => {
    router.back();
  };

  // Show loading state if:
  // 1. Service data hasn't loaded yet (either current or historical)
  // 2. AIM cluster model is still loading after service data arrives
  const isLoadingFirstQuery =
    (isLoadingAimService || isLoadingAimServiceHistory) &&
    !isAimServiceError &&
    !isAimServiceHistoryError;
  const isLoadingSecondQuery =
    !!resourceName && !aimClusterModel && !isAimError;
  const isLoading = isLoadingFirstQuery || isLoadingSecondQuery;

  if (isLoading) {
    return (
      <div className="flex flex-col space-y-6 py-6">
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

  const hasServiceError =
    (!_isHistorical && isAimServiceError) ||
    (_isHistorical && !_isNotFoundError);
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

  const parsedAim = !_isHistorical
    ? aimParser(aimClusterModel, aimService ? [aimService] : undefined)
    : historicalAimParser(aimClusterModel, historicalService);
  const deployedService = parsedAim.deployedService;
  const aimConditions = deployedService?.status?.conditions;
  const { external, internal } = deployedService?.endpoints || {};
  const externalHost = external ? `${external}/v1/chat/completions` : '';
  const internalHost = internal ? `${internal}/v1/chat/completions` : '';

  // Construct workload object for WorkloadLogsModal
  const aimWorkload: ResourceMetrics = {
    id,
    name: parsedAim.resourceName,
    displayName: parsedAim.title || parsedAim.resourceName,
    type: WorkloadType.INFERENCE,
    status:
      (deployedService?.status.status as unknown as WorkloadStatus) ??
      WorkloadStatus.UNKNOWN,
    gpuCount: null,
    vram: null,
    createdAt: deployedService?.metadata?.creationTimestamp ?? null,
    createdBy: null,
    resourceType: ResourceType.AIM_SERVICE,
  };

  // Show only "{*}Ready" conditions, filter out anything else.
  const sortedConditions = (aimConditions ?? [])
    .filter(
      (condition) =>
        condition.type !== 'Ready' && condition.type?.endsWith('Ready'),
    )
    // pre-compute status
    .map((condition) => ({
      ...condition,
      computedStatus: getConditionStatus(condition),
    }))
    // sort: Failed → Pending → Ready
    .sort(
      (a, b) => statusOrder[a.computedStatus] - statusOrder[b.computedStatus],
    );

  return (
    <div className="flex flex-col space-y-6 py-6">
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
            <h2>{parsedAim.canonicalName}</h2>
            <StatusDisplay
              type={deployedService?.status.status as string}
              variants={getAIMServiceStatusVariants(t)}
              additionalProps={{ isShowBackground: true, isTextColored: true }}
            />
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex space-x-2">
          <ActionButton
            secondary
            onPress={() =>
              router.push({ pathname: '/chat', query: { workload: id } })
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
          <InferenceMetrics workloadId={id} />
        )}

      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">{t('list.headers.aim.title')}</h3>
      </div>

      <div className="columns-1 md:columns-2 xl:columns-3 gap-6 space-y-6">
        {/* AIM Information */}
        {(aimClusterModel || isLoadingAim) && (
          <Card className="break-inside-avoid mb-6 border-1 border-default-200 shadow-sm">
            <CardHeader className="py-4 px-6 flex items-center">
              <h3 className="text-base font-semibold flex items-center space-x-2">
                <IconDatabase size={16} className="text-default-500" />
                <span>{t('details.sections.basicInformation')}</span>
              </h3>
            </CardHeader>
            <CardBody className="space-y-4 px-6 pb-6 pt-0">
              {isLoadingAim ? (
                <div className="flex flex-col space-y-4">
                  <Skeleton className="w-full h-6 rounded-lg" />
                  <Skeleton className="w-3/4 h-6 rounded-lg" />
                  <Skeleton className="w-2/3 h-6 rounded-lg" />
                  <Skeleton className="w-1/2 h-6 rounded-lg" />
                </div>
              ) : (
                <div className="flex flex-col space-y-4">
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
                        {parsedAim.resourceName || '—'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-end justify-between gap-3 w-full">
                    <div>
                      <h5 className="text-sm text-default-700">
                        {t('models:deployAIMDrawer.fields.metric.title')}
                      </h5>
                      {templatesLoading ? (
                        <Skeleton className="mt-1 h-4 w-32 rounded" />
                      ) : (
                        <p className="font-mono text-sm">
                          {t(
                            `models:performanceMetrics.values.${(aimService?.spec?.overrides?.metric as string) || AIMMetric.Default}`,
                          )}
                        </p>
                      )}
                    </div>
                    {!templatesLoading && isMetricUnoptimized && (
                      <UnoptimizedProfileBadge
                        label={t(
                          'models:deployAIMDrawer.fields.metric.unoptimizedLabel',
                        )}
                      />
                    )}
                  </div>

                  {aimClusterModel!.status?.imageMetadata?.model
                    ?.canonicalName && (
                    <div className="flex items-center space-x-3">
                      <div>
                        <h5 className="text-sm text-default-700">
                          {t('list.headers.aim.canonicalName')}
                        </h5>
                        <p className="font-mono text-sm">
                          {
                            aimClusterModel!.status.imageMetadata.model
                              .canonicalName
                          }
                        </p>
                      </div>
                    </div>
                  )}

                  {aimClusterModel!.status?.imageMetadata?.originalLabels
                    ?.orgOpencontainersImageDescription && (
                    <div className="flex items-center space-x-3">
                      <div>
                        <h5 className="text-sm text-default-700">
                          {t('list.headers.aim.description')}
                        </h5>
                        <p className="text-sm">
                          {
                            aimClusterModel!.status.imageMetadata.originalLabels
                              .orgOpencontainersImageDescription
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

                  <div className="flex items-center space-x-3">
                    <div>
                      <h5 className="text-sm text-default-700">
                        {t('list.headers.createdAt.title')}
                      </h5>
                      <DateDisplay
                        date={
                          deployedService?.metadata?.creationTimestamp as string
                        }
                      />
                    </div>
                  </div>
                </div>
              )}
            </CardBody>
          </Card>
        )}
        {/* Status */}
        <Card className="break-inside-avoid mb-6 border-1 border-default-200 shadow-sm">
          <CardHeader className="py-4 px-6 flex items-center">
            <h3 className="text-base font-semibold flex items-center space-x-2">
              <IconDashboard size={16} className="text-default-500" />
              <span>{t('details.sections.status')}</span>
            </h3>
          </CardHeader>
          <CardBody className="px-6 pb-6 pt-0">
            {Array.isArray(sortedConditions) && sortedConditions.length > 0 ? (
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
                  <div className="space-y-4">
                    {sortedConditions.map((condition) => (
                      <div
                        key={condition.type}
                        className="flex items-start justify-between border-b border-default-100 pb-4 last:border-b-0 last:pb-0"
                      >
                        <div className="flex flex-col">
                          <span className="font-medium text-sm">
                            {/* Remove "Ready" suffix: CacheReady → Cache */}
                            {condition.type.replace(/Ready$/, '')}
                          </span>
                          <span className="text-xs text-default-400">
                            {displayTimestamp(
                              new Date(condition.lastTransitionTime),
                            )}
                          </span>
                          {condition.message && (
                            <p className="text-xs text-default-500 mt-1">
                              {condition.message}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-1.5 shrink-0">
                          <Status
                            {...getConditionStatusProps(
                              condition.computedStatus,
                              t,
                            )}
                            isShowBackground={false}
                            isTextColored={true}
                            size="sm"
                          />
                        </div>
                      </div>
                    ))}
                  </div>
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
        {(externalHost || internalHost) && (
          <Card className="break-inside-avoid mb-6 border-1 border-default-200 shadow-sm">
            <CardHeader className="py-4 px-6 flex items-center">
              <h3 className="text-base font-semibold flex items-center space-x-2">
                <IconWorld size={16} className="text-default-500" />
                <span>{t('details.sections.output')}</span>
              </h3>
            </CardHeader>
            <CardBody className="space-y-3 px-6 pb-6 pt-0">
              {externalHost && deployedService?.clusterAuthGroupId && (
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
              {!deployedService?.clusterAuthGroupId && (
                <div className="flex items-start gap-2 rounded-lg border border-warning-200 bg-warning-50/50 p-3 dark:border-warning-500/30 dark:bg-warning-500/10">
                  <IconAlertTriangle
                    size={16}
                    className="text-warning-500 mt-0.5 shrink-0"
                  />
                  <p className="text-sm text-default-600">
                    {t('details.fields.notManagedByWorkbench')}
                  </p>
                </div>
              )}
            </CardBody>
          </Card>
        )}
        {/* Autoscaling Status Card */}
        {aimService?.spec?.autoScaling && (
          <ScalingStatusCard
            spec={aimService.spec}
            runtime={aimService.status.runtime}
            namespace={namespace ?? undefined}
            id={id}
            onSettingsSaved={() => refetchAimService()}
          />
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
          logSource={LogSource.AIM}
          namespace={namespace as string}
        />
      )}
    </div>
  );
};

export async function getServerSideProps(context: {
  req: any;
  res: any;
  locale: any;
  params: any;
  query: any;
}) {
  const { req, res, locale, params, query } = context;

  const session = await getServerSession(req, res, authOptions);

  if (
    !session ||
    !session.user ||
    !session.user.email ||
    !session.accessToken
  ) {
    return {
      redirect: {
        destination: '/',
        permanent: false,
      },
    };
  }

  const id = params?.id;

  if (!id) {
    return {
      redirect: {
        destination: '/models',
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
        href: prevNavItem.href,
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
